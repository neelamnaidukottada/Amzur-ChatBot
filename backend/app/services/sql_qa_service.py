"""Service for natural-language questions over SQL databases."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url

from app.ai.llm import get_chat_llm

logger = logging.getLogger(__name__)


_ALLOWED_DIALECTS = {"sqlite", "postgresql"}


@dataclass
class SQLQAResult:
    """Result returned by the SQL QA service."""

    question: str
    sql: str
    rows: List[Dict[str, Any]]
    answer: str


class SQLQAService:
    """Translate natural language to SQL and execute it safely (read-only)."""

    def __init__(self, max_rows: int = 100) -> None:
        self.max_rows = max_rows

    def answer_question(self, database_url: str, question: str) -> SQLQAResult:
        """Generate SQL from question, run it, and summarize the answer."""
        if not question.strip():
            raise ValueError("question is required")

        safe_url = self._validate_database_url(database_url)
        schema_summary = self._get_schema_summary(safe_url)

        sql = self._generate_sql(question=question, schema_summary=schema_summary)
        sql = self._sanitize_sql(sql)

        rows = self._execute_read_only_query(safe_url, sql)
        answer = self._summarize_answer(question=question, sql=sql, rows=rows)

        return SQLQAResult(question=question, sql=sql, rows=rows, answer=answer)

    def _validate_database_url(self, database_url: str) -> str:
        if not database_url or not database_url.strip():
            raise ValueError("database_url is required")

        try:
            url_obj: URL = make_url(database_url.strip())
        except Exception as exc:
            raise ValueError(f"Invalid database URL: {exc}") from exc

        dialect = (url_obj.drivername or "").split("+")[0]
        if dialect not in _ALLOWED_DIALECTS:
            allowed = ", ".join(sorted(_ALLOWED_DIALECTS))
            raise ValueError(f"Unsupported database dialect '{dialect}'. Allowed: {allowed}")

        return database_url.strip()

    def _get_schema_summary(self, database_url: str) -> str:
        engine = self._create_engine(database_url)
        try:
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            if not table_names:
                raise ValueError("No tables found in the target database")

            lines: List[str] = []
            for table_name in sorted(table_names):
                columns = inspector.get_columns(table_name)
                col_parts = []
                for col in columns:
                    col_name = col.get("name", "unknown")
                    col_type = str(col.get("type", "unknown"))
                    col_parts.append(f"{col_name} ({col_type})")
                joined = ", ".join(col_parts)
                lines.append(f"- {table_name}: {joined}")

            return "\n".join(lines)
        finally:
            engine.dispose()

    def _generate_sql(self, question: str, schema_summary: str) -> str:
        llm = get_chat_llm()
        prompt = (
            "You are a SQL expert. Generate one SQL query for the user question.\n"
            "Rules:\n"
            "1) Use only tables/columns from the schema.\n"
            "2) Return read-only SQL only (SELECT or WITH ... SELECT).\n"
            "3) Never use INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/TRUNCATE.\n"
            "4) Prefer explicit column names and deterministic ordering.\n"
            "5) Limit results to 100 rows unless question asks fewer.\n"
            "6) Output ONLY raw SQL text. No markdown, no explanation.\n\n"
            f"Schema:\n{schema_summary}\n\n"
            f"Question: {question}"
        )

        response = llm.invoke(prompt)
        sql = getattr(response, "content", "") if hasattr(response, "content") else str(response)
        if not sql or not str(sql).strip():
            raise RuntimeError("Model did not generate SQL")

        return str(sql).strip()

    def _sanitize_sql(self, sql: str) -> str:
        cleaned = sql.strip().strip("`")
        cleaned = re.sub(r"^```sql\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        if ";" in cleaned:
            parts = [p.strip() for p in cleaned.split(";") if p.strip()]
            if len(parts) != 1:
                raise ValueError("Only a single SQL statement is allowed")
            cleaned = parts[0]

        lowered = cleaned.lower().strip()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise ValueError("Only read-only SELECT queries are allowed")

        forbidden = [
            " insert ",
            " update ",
            " delete ",
            " drop ",
            " alter ",
            " create ",
            " truncate ",
            " grant ",
            " revoke ",
            " vacuum ",
            " call ",
            " execute ",
            " merge ",
        ]
        padded = f" {lowered} "
        for token in forbidden:
            if token in padded:
                raise ValueError("Query contains a forbidden SQL operation")

        if not re.search(r'\blimit\b', lowered):
            cleaned = f"{cleaned} LIMIT {self.max_rows}"

        return cleaned

    def _execute_read_only_query(self, database_url: str, sql: str) -> List[Dict[str, Any]]:
        engine = self._create_engine(database_url)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchmany(self.max_rows)
                serialized: List[Dict[str, Any]] = []
                for row in rows:
                    row_dict = dict(row._mapping)
                    serialized.append({k: self._json_safe(v) for k, v in row_dict.items()})
                return serialized
        finally:
            engine.dispose()

    def _summarize_answer(self, question: str, sql: str, rows: List[Dict[str, Any]]) -> str:
        llm = get_chat_llm()
        rows_json = json.dumps(rows, default=str)
        prompt = (
            "Answer the user's question using SQL results.\n"
            "Be concise and factual.\n"
            "If no rows are returned, clearly say no matching data was found.\n"
            f"Question: {question}\n"
            f"SQL: {sql}\n"
            f"Rows JSON: {rows_json}"
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", "") if hasattr(response, "content") else str(response)
        return str(content).strip()

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _create_engine(database_url: str):
        """Create SQLAlchemy engine with Supabase SSL settings when needed."""
        connect_args = {"sslmode": "require"} if "supabase" in database_url.lower() else {}
        return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


_sql_qa_service: Optional[SQLQAService] = None


def get_sql_qa_service() -> SQLQAService:
    """Get singleton SQL QA service."""
    global _sql_qa_service
    if _sql_qa_service is None:
        _sql_qa_service = SQLQAService()
    return _sql_qa_service
