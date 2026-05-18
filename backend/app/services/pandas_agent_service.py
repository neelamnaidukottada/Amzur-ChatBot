"""LangChain Pandas DataFrame Agent Service for natural language data analysis."""

import logging
import re
import pandas as pd
from typing import Optional, Dict, Any
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_core.tools import Tool

from app.ai.llm import get_chat_llm

logger = logging.getLogger(__name__)


class PandasAgentResponse:
    """Response from pandas agent query."""

    def __init__(self, answer: str, reasoning: Optional[str] = None):
        self.answer = answer
        self.reasoning = reasoning


class PandasAgentService:
    """Service for querying dataframes using LangChain Pandas Agent."""

    def __init__(self):
        """Initialize the pandas agent service."""
        self.llm = get_chat_llm()
        logger.info("[PandasAgentService] Initialized")

    def create_agent(self, df: pd.DataFrame, verbose: bool = False):
        """
        Create a pandas dataframe agent for natural language queries.

        Args:
            df: The pandas DataFrame to query
            verbose: Enable verbose output from agent

        Returns:
            LangChain agent executor
        """
        try:
            logger.info(
                f"[PandasAgentService] Creating agent for DataFrame: "
                f"{len(df)} rows, {len(df.columns)} columns"
            )

            # Create the pandas dataframe agent
            agent = create_pandas_dataframe_agent(
                llm=self.llm,
                df=df,
                verbose=verbose,
                # Required by current langchain-experimental pandas agent toolkit.
                allow_dangerous_code=True,
                agent_type="tool-calling",
            )

            logger.info("[PandasAgentService] Agent created successfully")
            return agent

        except Exception as exc:
            logger.error(
                f"[PandasAgentService] Error creating agent: {str(exc)}", exc_info=True
            )
            raise ValueError(f"Failed to create pandas agent: {str(exc)}")

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    def _deterministic_sum_answer(self, df: pd.DataFrame, question: str, source: str) -> Optional[Dict[str, Any]]:
        """Return exact SUM result for simple aggregate questions when possible."""
        q = (question or "").lower()
        # Require explicit aggregation intent — phrases like "total rows" or "overview" must NOT trigger this.
        _agg_patterns = [
            r'\bsum\s+of\b',
            r'\btotal\s+of\b',
            r'\bwhat\s+is\s+the\s+(sum|total)\b',
            r'\bcalculate\s+(the\s+)?(sum|total)\b',
            r'\bfind\s+(the\s+)?(sum|total)\b',
            r'\bget\s+(the\s+)?(sum|total)\b',
            r'\b(sum|total)\s+(of\s+)?(spent|amount|price|cost|revenue|sales|value|expense|income)\b',
        ]
        if not any(re.search(pat, q) for pat in _agg_patterns):
            return None

        if df.empty or len(df.columns) == 0:
            return None

        norm_to_col = {self._normalize_key(str(col)): str(col) for col in df.columns}

        # Try explicit "sum of <column>" extraction first.
        col_hint = None
        match = re.search(r"(?:sum|total)\s+of\s+([a-zA-Z0-9_\-\s]+)", question, flags=re.IGNORECASE)
        if match:
            col_hint = match.group(1).strip()

        candidate_col = None
        if col_hint:
            hint_norm = self._normalize_key(col_hint)
            if hint_norm in norm_to_col:
                candidate_col = norm_to_col[hint_norm]
            else:
                for norm_key, original in norm_to_col.items():
                    if hint_norm and (hint_norm in norm_key or norm_key in hint_norm):
                        candidate_col = original
                        break

        # Fallback: if no clear hint, pick a likely monetary/numeric column.
        if candidate_col is None:
            preferred_names = ["totalspent", "amount", "total", "spent", "price", "cost", "revenue", "sales"]
            for pref in preferred_names:
                for norm_key, original in norm_to_col.items():
                    if pref in norm_key:
                        candidate_col = original
                        break
                if candidate_col:
                    break

        if candidate_col is None:
            return None

        numeric = pd.to_numeric(
            df[candidate_col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
            errors="coerce",
        )
        if numeric.notna().sum() == 0:
            return None

        total_value = float(numeric.sum())
        answer = f'The sum of "{candidate_col}" is {total_value:,.2f}.'

        return {
            "success": True,
            "question": question,
            "answer": answer,
            "source": source,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
        }

    def query(
        self,
        df: pd.DataFrame,
        question: str,
        source: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Query a dataframe with a natural language question.

        Args:
            df: The pandas DataFrame
            question: The natural language question
            source: Source identifier (file name, sheet name, etc.)

        Returns:
            Dictionary with answer and metadata
        """
        try:
            logger.info(
                f"[PandasAgentService] Query received - Question: {question}"
            )
            logger.info(f"[PandasAgentService] DataFrame info - {len(df)} rows, {len(df.columns)} columns")

            # Use deterministic computation for simple SUM questions to avoid LLM arithmetic drift.
            deterministic = self._deterministic_sum_answer(df=df, question=question, source=source)
            if deterministic is not None:
                logger.info("[PandasAgentService] Deterministic SUM path used")
                return deterministic

            # Create agent for this dataframe
            agent = self.create_agent(df, verbose=False)

            # Execute the query
            logger.info("[PandasAgentService] Executing agent with question...")
            result = agent.invoke({"input": question})

            # Extract the answer
            answer = result.get("output", str(result))

            logger.info(
                f"[PandasAgentService] Query completed - Answer length: {len(answer)} chars"
            )

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "source": source,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
            }

        except Exception as exc:
            logger.error(
                f"[PandasAgentService] Error processing query: {str(exc)}",
                exc_info=True,
            )

            return {
                "success": False,
                "question": question,
                "error": str(exc),
                "source": source,
            }

    def query_with_context(
        self,
        df: pd.DataFrame,
        question: str,
        context: Optional[str] = None,
        source: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Query a dataframe with optional context for follow-up questions.

        Args:
            df: The pandas DataFrame
            question: The natural language question
            context: Optional context from previous queries
            source: Source identifier

        Returns:
            Dictionary with answer and metadata
        """
        try:
            # Build enhanced prompt with context
            if context:
                enhanced_question = f"Context from previous analysis: {context}\n\nNow answer: {question}"
            else:
                enhanced_question = question

            logger.info(
                f"[PandasAgentService] Query with context - Question: {question}"
            )

            # Create agent and execute
            agent = self.create_agent(df, verbose=False)
            result = agent.invoke({"input": enhanced_question})
            answer = result.get("output", str(result))

            logger.info(
                f"[PandasAgentService] Context-aware query completed"
            )

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "source": source,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "has_context": context is not None,
            }

        except Exception as exc:
            logger.error(
                f"[PandasAgentService] Error in context query: {str(exc)}",
                exc_info=True,
            )

            return {
                "success": False,
                "question": question,
                "error": str(exc),
                "source": source,
                "has_context": context is not None,
            }

    def get_dataframe_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get a summary of the dataframe structure and content.

        Args:
            df: The pandas DataFrame

        Returns:
            Dictionary with dataframe metadata
        """
        try:
            # Get basic statistics
            numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

            summary = {
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "columns": list(df.columns),
                "dtypes": {str(col): str(dtype) for col, dtype in df.dtypes.items()},
                "column_categories": {
                    "numerical": numerical_cols,
                    "categorical": categorical_cols,
                    "datetime": datetime_cols,
                },
                "missing_values": df.isnull().sum().to_dict(),
                "sample_rows": df.head(3).to_dict(orient="records"),
            }

            logger.info(
                f"[PandasAgentService] Generated dataframe summary: {len(df)} rows"
            )

            return summary

        except Exception as exc:
            logger.error(
                f"[PandasAgentService] Error generating summary: {str(exc)}",
                exc_info=True,
            )
            raise ValueError(f"Failed to generate dataframe summary: {str(exc)}")


def get_pandas_agent_service() -> PandasAgentService:
    """Get or create pandas agent service instance."""
    return PandasAgentService()
