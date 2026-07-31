import psycopg2
try:
    conn = psycopg2.connect(dbname="yourdatabase", user="root", password="rootpassword", host="127.0.0.1")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ALTER ROLE nl2sql_reader WITH PASSWORD 'yourpassword';")
    print("Success root")
except Exception as e:
    print(f"Failed root: {e}")

try:
    conn = psycopg2.connect(dbname="yourdatabase", user="postgres", password="rootpassword", host="127.0.0.1")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ALTER ROLE nl2sql_reader WITH PASSWORD 'yourpassword';")
    print("Success postgres")
except Exception as e:
    print(f"Failed postgres: {e}")
