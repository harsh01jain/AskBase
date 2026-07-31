-- Create the read-only role
CREATE ROLE nl2sql_reader WITH LOGIN PASSWORD 'yourpassword';
GRANT CONNECT ON DATABASE yourdatabase TO nl2sql_reader;
GRANT USAGE ON SCHEMA public TO nl2sql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nl2sql_reader;

-- Ensure future tables also get SELECT grants
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO nl2sql_reader;

-- Apply timeouts
ALTER ROLE nl2sql_reader SET statement_timeout = '15s';
ALTER ROLE nl2sql_reader SET idle_in_transaction_session_timeout = '30s';
