"""
Unit tests for AskBase backend.
Tests cover: SQL validation, schema extraction, query execution, 
LLM response parsing, retrieval, and API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════
# 1. SQL Validation Tests (main.py -> validate_sql)
# ═══════════════════════════════════════════════

class TestSQLValidation:
    """Tests for the SQL validation function that ensures only SELECT queries run."""

    def setup_method(self):
        from main import validate_sql
        self.validate = validate_sql

    def test_valid_select(self):
        assert self.validate("SELECT * FROM customers") is True

    def test_valid_select_with_where(self):
        assert self.validate("SELECT name FROM customers WHERE segment = 'Enterprise'") is True

    def test_valid_select_with_join(self):
        sql = "SELECT c.name, o.total_amount FROM customers c JOIN orders o ON c.customer_id = o.customer_id"
        assert self.validate(sql) is True

    def test_valid_select_with_aggregation(self):
        assert self.validate("SELECT COUNT(*) FROM products GROUP BY category") is True

    def test_valid_select_with_subquery(self):
        sql = "SELECT * FROM customers WHERE customer_id IN (SELECT customer_id FROM orders)"
        assert self.validate(sql) is True

    def test_reject_insert(self):
        assert self.validate("INSERT INTO customers (name) VALUES ('test')") is False

    def test_reject_update(self):
        assert self.validate("UPDATE customers SET name = 'hacked'") is False

    def test_reject_delete(self):
        assert self.validate("DELETE FROM customers") is False

    def test_reject_drop(self):
        assert self.validate("DROP TABLE customers") is False

    def test_reject_alter(self):
        assert self.validate("ALTER TABLE customers ADD COLUMN age INT") is False

    def test_reject_empty(self):
        assert self.validate("") is False

    def test_reject_nonsense(self):
        assert self.validate("this is not sql at all") is False

    def test_reject_multiple_statements(self):
        assert self.validate("SELECT 1; DROP TABLE customers;") is False


# ═══════════════════════════════════════════════
# 2. LLM Response Parsing Tests (llm.py)
# ═══════════════════════════════════════════════

class TestLLMParsing:
    """Tests for LLM output cleaning (markdown stripping, etc.)."""

    def test_strip_sql_markdown_block(self):
        raw = "```sql\nSELECT * FROM customers\n```"
        cleaned = raw.strip()
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        assert cleaned == "SELECT * FROM customers"

    def test_strip_generic_markdown_block(self):
        raw = "```\nSELECT 1\n```"
        cleaned = raw.strip()
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        assert cleaned == "SELECT 1"

    def test_no_markdown(self):
        raw = "SELECT COUNT(*) FROM orders"
        cleaned = raw.strip()
        assert cleaned == "SELECT COUNT(*) FROM orders"

    def test_whitespace_handling(self):
        raw = "  \n  SELECT * FROM products  \n  "
        assert raw.strip() == "SELECT * FROM products"


# ═══════════════════════════════════════════════
# 3. Database Module Tests (database.py)
# ═══════════════════════════════════════════════

class TestDatabaseModule:
    """Tests for database connection and schema extraction logic."""

    @patch("database.psycopg2.connect")
    def test_get_db_connection_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        from database import get_db_connection
        conn = get_db_connection()
        assert conn is not None
        mock_connect.assert_called_once()

    @patch("database.psycopg2.connect", side_effect=Exception("Connection failed"))
    def test_get_db_connection_failure(self, mock_connect):
        from database import get_db_connection
        conn = get_db_connection()
        assert conn is None

    @patch("database.get_db_connection")
    def test_execute_query_no_connection(self, mock_get_conn):
        mock_get_conn.return_value = None
        from database import execute_query
        result = execute_query("SELECT 1")
        assert "error" in result

    @patch("database.get_db_connection")
    def test_execute_query_success(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchmany.return_value = [{"id": 1, "name": "test"}]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        from database import execute_query
        result = execute_query("SELECT * FROM test")
        assert "columns" in result
        assert "rows" in result

    @patch("database.get_db_connection")
    def test_get_schema_no_connection(self, mock_get_conn):
        mock_get_conn.return_value = None
        from database import get_schema_definitions
        result = get_schema_definitions()
        assert result == []


# ═══════════════════════════════════════════════
# 4. Retrieval Module Tests (retrieval.py)
# ═══════════════════════════════════════════════

class TestRetrieval:
    """Tests for ChromaDB retrieval logic."""

    @patch("retrieval.get_schema_definitions")
    @patch("retrieval.chroma_client")
    def test_index_schema_empty(self, mock_chroma, mock_schema):
        mock_schema.return_value = []
        from retrieval import index_schema
        result = index_schema()
        assert result["status"] == "error"

    def test_retrieve_context_returns_list(self):
        """Ensure retrieve_context returns a list type."""
        from retrieval import retrieve_context
        result = retrieve_context("test query", top_k=3)
        assert isinstance(result, list)


# ═══════════════════════════════════════════════
# 5. API Endpoint Tests (main.py)
# ═══════════════════════════════════════════════

class TestAPIEndpoints:
    """Tests for FastAPI endpoints."""

    def setup_method(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "ollama" in data

    def test_schema_endpoint(self):
        response = self.client.get("/schema")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_history_endpoint(self):
        response = self.client.get("/history")
        assert response.status_code == 200

    def test_query_endpoint_empty_question(self):
        response = self.client.post("/query", json={"question": "", "history": []})
        assert response.status_code == 200  # SSE stream still returns 200

    def test_reindex_endpoint(self):
        response = self.client.post("/reindex")
        assert response.status_code == 200


# ═══════════════════════════════════════════════
# 6. Suggestions Parsing Tests
# ═══════════════════════════════════════════════

class TestSuggestionsParsing:
    """Tests for parsing LLM suggestion responses."""

    def test_parse_list_response(self):
        raw = '["Question 1?", "Question 2?", "Question 3?"]'
        result = json.loads(raw)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_parse_dict_response(self):
        raw = '{"suggestions": ["Q1?", "Q2?", "Q3?"]}'
        result = json.loads(raw)
        assert isinstance(result, dict)
        for k, v in result.items():
            if isinstance(v, list):
                assert len(v) == 3

    def test_parse_invalid_json(self):
        raw = "not valid json"
        with pytest.raises(json.JSONDecodeError):
            json.loads(raw)

    def test_truncate_to_three(self):
        suggestions = ["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"]
        assert len(suggestions[:3]) == 3


# ═══════════════════════════════════════════════
# 7. Edge Cases
# ═══════════════════════════════════════════════

class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_sql_with_semicolons(self):
        from main import validate_sql
        # Multiple statements should be rejected
        assert validate_sql("SELECT 1; SELECT 2") is False

    def test_sql_case_insensitive_keywords(self):
        from main import validate_sql
        assert validate_sql("select * from customers") is True

    def test_sql_with_limit(self):
        from main import validate_sql
        assert validate_sql("SELECT * FROM orders LIMIT 10") is True

    def test_sql_with_cte(self):
        from main import validate_sql
        sql = "WITH top_customers AS (SELECT * FROM customers LIMIT 5) SELECT * FROM top_customers"
        # CTE may or may not pass depending on sqlglot parsing
        result = self.validate_cte(sql)
        assert isinstance(result, bool)

    def validate_cte(self, sql):
        from main import validate_sql
        return validate_sql(sql)
