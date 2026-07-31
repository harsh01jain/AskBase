import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "nl2sql_reader")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "yourpassword")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "yourdatabase")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
        # Apply timeout settings per the project requirements
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 15000;") # 15 seconds
            cur.execute("SET idle_in_transaction_session_timeout = 30000;")
        conn.commit()
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def execute_query(query: str, limit: int = 1000):
    """Executes a validated SELECT query and returns the results."""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        # We assume query validation is done BEFORE calling this function
        # Enforce a soft limit by injecting it if not present, though we can just wrap it
        # Actually it's safer to run it as a subquery if we want to force limit, 
        # or rely on sqlglot to inject limit. For now we just execute.
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchmany(limit)
            return {"columns": [desc[0] for desc in cur.description], "rows": results}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def get_schema_definitions():
    """Extracts schema definitions for indexing."""
    conn = get_db_connection()
    if not conn:
        return []
    
    schema_query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'public';
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(schema_query)
            rows = cur.fetchall()
            
            tables = {}
            for row in rows:
                t_name = row['table_name']
                if t_name not in tables:
                    tables[t_name] = []
                tables[t_name].append(f"{row['column_name']} ({row['data_type']})")
                
            schema_docs = []
            for t_name, columns in tables.items():
                schema_docs.append({
                    "table": t_name,
                    "description": f"Table: {t_name}. Columns: {', '.join(columns)}"
                })
            return schema_docs
    except Exception as e:
        print(f"Schema extraction error: {e}")
        return []
    finally:
        if conn:
            conn.close()

ADMIN_USER = os.getenv("POSTGRES_ADMIN_USER", "root")
ADMIN_PASS = os.getenv("POSTGRES_ADMIN_PASSWORD", "rootpassword")

def get_admin_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=ADMIN_USER,
            password=ADMIN_PASS,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
    except Exception as e:
        print(f"Admin connection error: {e}")
        return None

def init_audit_table():
    conn = get_admin_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_audit (
                    id SERIAL PRIMARY KEY,
                    question TEXT,
                    generated_sql TEXT,
                    attempts INT,
                    latency_ms INT,
                    status VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    except Exception as e:
        print(f"Audit table init error: {e}")
    finally:
        conn.close()

def insert_audit_log(question, generated_sql, attempts, latency_ms, status):
    conn = get_admin_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO query_audit (question, generated_sql, attempts, latency_ms, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (question, generated_sql, attempts, latency_ms, status))
        conn.commit()
    except Exception as e:
        print(f"Audit insert error: {e}")
    finally:
        conn.close()

def get_audit_history(limit=50):
    conn = get_admin_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM query_audit ORDER BY timestamp DESC LIMIT %s", (limit,))
            # Convert datetime to string for JSON serialization
            rows = cur.fetchall()
            for r in rows:
                if r.get('timestamp'):
                    r['timestamp'] = r['timestamp'].isoformat()
            return rows
    except Exception as e:
        print(f"Audit fetch error: {e}")
        return []
    finally:
        conn.close()

init_audit_table()
