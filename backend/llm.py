import os
import requests
import json
from typing import Dict, Any

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

def generate_sql(question: str, schema_context: list[str], history: list = None, error_context: str = None) -> str:
    """Calls Ollama to generate a SQL query."""
    
    schema_str = "\n".join(schema_context)
    
    prompt = f"""You are a PostgreSQL expert. Your task is to generate a fully correct PostgreSQL query to answer the user's question.
    
CRITICAL RULES:
1. You MUST ONLY use the tables and columns explicitly listed in the Schema context below.
2. DO NOT invent or assume any table or column names that are not in the schema.
3. If a concept (like "enterprise") maps to a column (like "segment"), use a WHERE clause on that column.
4. ALWAYS use ILIKE for string comparisons to ensure case-insensitivity (e.g., segment ILIKE '%enterprise%').
    
Schema context:
{schema_str}

"""
    if history and len(history) > 0:
        prompt += "\n--- PREVIOUS CHAT HISTORY ---\n"
        for h in history[-3:]:
            prompt += f"Question: {h.get('question')}\nSQL: {h.get('sql')}\n\n"
        prompt += "--- END HISTORY ---\n"
    if error_context:
        prompt += f"\nThe previous query failed with this error. Please correct it:\n{error_context}\n"
        
    prompt += f"\nQuestion: {question}\n\nRespond ONLY with the raw SQL query, no markdown formatting, no explanation."
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        sql = data.get("response", "").strip()
        
        # Remove potential markdown block if the model ignores the instruction
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return ""

import httpx

async def stream_explanation(question: str, sql: str):
    prompt = f"You are a helpful data analyst. Explain this SQL query in plain English in 1-2 concise sentences. Be very brief.\nQuestion: {question}\nSQL: {sql}\nExplanation:"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30.0) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                    except:
                        pass

async def generate_suggestions(question: str, sql: str) -> list:
    prompt = f"Given the user's question: '{question}' and the generated SQL: '{sql}', provide exactly 3 short follow-up questions the user could ask next to dig deeper into this data. Return ONLY a JSON list of strings, for example: [\"Question 1?\", \"Question 2?\", \"Question 3?\"]. Do not include any markdown formatting or explanation."
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=15.0)
            data = response.json()
            result_text = data.get("response", "[]")
            suggestions = json.loads(result_text)
            if isinstance(suggestions, dict):
                # sometimes models return {"suggestions": [...]}
                for k, v in suggestions.items():
                    if isinstance(v, list):
                        return v[:3]
                return []
            elif isinstance(suggestions, list):
                return suggestions[:3]
            return []
    except Exception as e:
        print(f"Suggestions Error: {e}")
        return []
