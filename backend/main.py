from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import sqlglot
import requests
import time
import json
import asyncio

from database import (
    execute_query, get_db_connection, get_schema_definitions,
    insert_audit_log, get_audit_history
)
from retrieval import index_schema, retrieve_context
from llm import generate_sql, stream_explanation, OLLAMA_BASE_URL

app = FastAPI(title="QueryLocal API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []

@app.get("/health")
def health_check():
    db_conn = get_db_connection()
    db_status = "ok" if db_conn else "error"
    if db_conn: db_conn.close()
        
    ollama_status = "error"
    try:
        r = requests.get(OLLAMA_BASE_URL, timeout=2)
        if r.status_code == 200: ollama_status = "ok"
    except: pass
        
    return {"database": db_status, "ollama": ollama_status}

@app.post("/reindex")
def trigger_reindex():
    return index_schema()

@app.get("/schema")
def schema():
    return get_schema_definitions()

@app.get("/history")
def history():
    return get_audit_history()

def validate_sql(sql: str) -> bool:
    try:
        parsed = sqlglot.parse(sql, read="postgres")
        if not parsed: return False
        for node in parsed:
            if not isinstance(node, sqlglot.exp.Select):
                return False
        return True
    except Exception:
        return False

@app.post("/query")
async def process_query(req: QueryRequest):
    async def event_stream():
        start_time = time.time()
        question = req.question
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Retrieving schema context...'})}\n\n"
        context = retrieve_context(question, top_k=5)
        
        max_attempts = 3
        attempt = 0
        error_msg = None
        sql = ""
        success = False
        result = None
        
        while attempt < max_attempts:
            attempt += 1
            yield f"data: {json.dumps({'type': 'status', 'message': f'Generating SQL (Attempt {attempt})...'})}\n\n"
            
            sql = generate_sql(question, context, history=req.history, error_context=error_msg)
            if not sql:
                error_msg = "LLM failed to return a query."
                continue
                
            yield f"data: {json.dumps({'type': 'status', 'message': f'Validating SQL (Attempt {attempt})...'})}\n\n"
            if not validate_sql(sql):
                error_msg = "Validation Error: Only SELECT queries are allowed, or the SQL is malformed."
                continue
                
            yield f"data: {json.dumps({'type': 'status', 'message': f'Executing SQL (Attempt {attempt})...'})}\n\n"
            result = execute_query(sql)
            if "error" in result:
                error_msg = result["error"]
                continue
                
            success = True
            break
            
        latency_ms = int((time.time() - start_time) * 1000)
        status_str = "Success" if success else "Failed"
        insert_audit_log(question, sql, attempt, latency_ms, status_str)
        
        if not success:
            payload = jsonable_encoder({'type': 'error', 'sql': sql, 'error': f'Failed after {max_attempts} attempts. Last error: {error_msg}', 'attempts': attempt})
            yield f"data: {json.dumps(payload)}\n\n"
            return
            
        # Success: stream initial payload
        payload = jsonable_encoder({'type': 'result', 'sql': sql, 'results': result, 'attempts': attempt, 'latency_ms': latency_ms})
        yield f"data: {json.dumps(payload)}\n\n"
        
        # Now stream the explanation token by token
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating explanation...'})}\n\n"
        
        from llm import generate_suggestions
        suggestions_task = asyncio.create_task(generate_suggestions(question, sql))
        
        try:
            async for token in stream_explanation(question, sql):
                yield f"data: {json.dumps({'type': 'explanation_token', 'token': token})}\n\n"
        except Exception as e:
            print(f"Explanation streaming error: {e}")
            
        try:
            suggestions = await asyncio.wait_for(suggestions_task, timeout=8.0)
            if suggestions:
                yield f"data: {json.dumps({'type': 'suggestions', 'data': suggestions})}\n\n"
        except Exception as e:
            print(f"Suggestions wait error: {e}")
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
