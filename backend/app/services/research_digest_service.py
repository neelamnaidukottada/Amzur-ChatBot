"""Autonomous research digest agent for arXiv."""

from __future__ import annotations

import asyncio
from datetime import date
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List
import json
import logging
import math
import re
from openai import OpenAI

from app.ai.llm import get_chat_llm
from app.core.settings import settings
from app.services.mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


class ResearchDigestService:
    """Runs autonomous multi-paper research digest workflow."""

    MIN_HIGH_QUALITY_PAPERS = 5

    def __init__(self) -> None:
        self.llm = get_chat_llm()
        self.embedding_client = OpenAI(
            api_key=settings.LITELLM_API_KEY,
            base_url=settings.LITELLM_PROXY_URL,
        )
        self.mcp_client = get_mcp_client()

    async def generate_digest_events(
        self,
        query: str,
        batch_size: int = 10,
        max_rounds: int = 3,
        categories: List[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        min_relevance_score: float = 0.70,
        min_quality_score: float = 0.68,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate NDJSON-friendly event objects for the full workflow."""

        normalized_query = query.strip()
        normalized_categories = [c.strip() for c in (categories or []) if c and c.strip()]
        if not normalized_query:
            raise ValueError("Query cannot be empty")

        yield {
            "type": "status",
            "stage": "start",
            "message": f"Starting autonomous research for: {normalized_query}",
            "data": {
                "categories": normalized_categories,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "min_relevance_score": min_relevance_score,
                "min_quality_score": min_quality_score,
            },
        }

        collected: Dict[str, Dict[str, Any]] = {}
        high_quality_count = 0
        rounds_completed = 0

        for round_index in range(max_rounds):
            start = round_index * batch_size
            rounds_completed = round_index + 1
            yield {
                "type": "status",
                "stage": "search",
                "message": f"Searching arXiv (round {rounds_completed}/{max_rounds})",
                "data": {"start": start, "batch_size": batch_size},
            }

            papers = await self._search_arxiv(
                query=normalized_query,
                start=start,
                max_results=batch_size,
                categories=normalized_categories,
                date_from=date_from,
                date_to=date_to,
            )
            if not papers:
                yield {
                    "type": "status",
                    "stage": "search",
                    "message": "No more matching papers returned by arXiv under current constraints.",
                }
                break

            scored = self._score_papers_with_embeddings(
                normalized_query,
                papers,
                min_relevance_score=min_relevance_score,
                min_quality_score=min_quality_score,
            )

            new_added = 0
            for paper in scored:
                if paper["id"] not in collected:
                    collected[paper["id"]] = paper
                    new_added += 1

            high_quality_count = sum(1 for p in collected.values() if p.get("high_quality"))
            yield {
                "type": "status",
                "stage": "evaluate",
                "message": "Evaluated relevance and quality using embeddings.",
                "data": {
                    "new_papers": new_added,
                    "total_unique": len(collected),
                    "high_quality_papers": high_quality_count,
                    "required_high_quality_papers": self.MIN_HIGH_QUALITY_PAPERS,
                },
            }

            if high_quality_count >= self.MIN_HIGH_QUALITY_PAPERS:
                yield {
                    "type": "status",
                    "stage": "decision",
                    "message": "Evidence threshold reached. Finalizing digest.",
                }
                break

        sorted_papers = sorted(
            collected.values(),
            key=lambda p: (p.get("high_quality", False), p.get("quality_score", 0.0), p.get("relevance_score", 0.0)),
            reverse=True,
        )

        selected_for_analysis = sorted_papers[: min(8, len(sorted_papers))]
        analyzed_papers: List[Dict[str, Any]] = []

        for idx, paper in enumerate(selected_for_analysis, start=1):
            yield {
                "type": "status",
                "stage": "analyze",
                "message": f"Analyzing paper {idx}/{len(selected_for_analysis)}",
                "data": {"title": paper["title"]},
            }
            analysis = self._analyze_single_paper(query=normalized_query, paper=paper)
            analyzed_papers.append(analysis)
            yield {
                "type": "paper_analysis",
                "stage": "analyze",
                "data": {
                    "title": analysis["title"],
                    "relevance_score": analysis["relevance_score"],
                    "quality_score": analysis["quality_score"],
                    "high_quality": analysis["high_quality"],
                },
            }

        keyword_clusters = self._cluster_keywords(analyzed_papers)
        consolidated = self._build_consolidated_digest(query=normalized_query, papers=analyzed_papers, keyword_clusters=keyword_clusters)

        decision = (
            "sufficient_evidence"
            if high_quality_count >= self.MIN_HIGH_QUALITY_PAPERS
            else "need_more_evidence"
        )

        final_payload = {
            "query": normalized_query,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason": (
                "Found sufficient high-quality relevant papers."
                if decision == "sufficient_evidence"
                else "Fewer than 5 high-quality relevant papers were found; broaden or refine search."
            ),
            "rounds_completed": rounds_completed,
            "min_required_high_quality_papers": self.MIN_HIGH_QUALITY_PAPERS,
            "high_quality_papers_found": high_quality_count,
            "total_unique_papers_scanned": len(collected),
            "filters": {
                "categories": normalized_categories,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "min_relevance_score": min_relevance_score,
                "min_quality_score": min_quality_score,
            },
            "papers": analyzed_papers,
            "keyword_clusters": keyword_clusters,
            "consolidated_research_digest": consolidated.get("consolidated_research_digest", ""),
            "trends": consolidated.get("trends", []),
            "conflicting_ideas": consolidated.get("conflicting_ideas", []),
            "next_action": (
                "Provide more search keywords or increase max_rounds."
                if decision == "need_more_evidence"
                else "Digest finalized."
            ),
        }

        final_payload["rendered_digest_text"] = self._render_digest_text(final_payload)

        yield {
            "type": "final",
            "stage": "complete",
            "data": final_payload,
        }

    async def _search_arxiv(
        self,
        query: str,
        start: int,
        max_results: int,
        categories: List[str],
        date_from: date | None,
        date_to: date | None,
    ) -> List[Dict[str, Any]]:
        search_query = self._build_arxiv_search_query(query=query, categories=categories)
        cumulative_results = await self.mcp_client.call_tool(
            "search_arxiv",
            {
                "query": search_query,
                "max_results": start + max_results,
            },
        )
        if not isinstance(cumulative_results, list):
            return []

        papers = self._normalize_mcp_papers(cumulative_results)
        paged_papers = papers[start:start + max_results]
        return self._apply_constraints(paged_papers, categories=categories, date_from=date_from, date_to=date_to)

    @staticmethod
    def _build_arxiv_search_query(query: str, categories: List[str]) -> str:
        text_clause = f"all:{query}"
        if not categories:
            return text_clause

        category_terms = [f"cat:{c}" for c in categories]
        category_clause = " OR ".join(category_terms)
        return f"({text_clause}) AND ({category_clause})"

    def _apply_constraints(
        self,
        papers: List[Dict[str, Any]],
        categories: List[str],
        date_from: date | None,
        date_to: date | None,
    ) -> List[Dict[str, Any]]:
        if not papers:
            return []

        category_set = {c.lower() for c in categories}
        filtered: List[Dict[str, Any]] = []

        for paper in papers:
            if category_set:
                paper_cats = {c.lower() for c in paper.get("categories", [])}
                if not paper_cats.intersection(category_set):
                    continue

            published_dt = None
            published = paper.get("published", "")
            if published:
                try:
                    published_dt = datetime.fromisoformat(published.replace("Z", "+00:00")).date()
                except Exception:
                    published_dt = None

            if date_from and published_dt and published_dt < date_from:
                continue
            if date_to and published_dt and published_dt > date_to:
                continue

            filtered.append(paper)

        return filtered

    def _normalize_mcp_papers(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        papers: List[Dict[str, Any]] = []

        for item in payload:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            summary = str(item.get("summary") or "").strip()
            published = str(item.get("published") or "").strip()
            authors = item.get("authors") if isinstance(item.get("authors"), list) else []
            categories = item.get("categories") if isinstance(item.get("categories"), list) else []
            paper_id = str(item.get("id") or url).strip()

            if not paper_id or not title or not url:
                continue

            papers.append(
                {
                    "id": paper_id,
                    "title": re.sub(r"\s+", " ", title),
                    "summary": re.sub(r"\s+", " ", summary),
                    "published": published,
                    "authors": [str(a).strip() for a in authors if str(a).strip()],
                    "categories": [str(c).strip() for c in categories if str(c).strip()],
                    "url": url,
                }
            )

        return papers

    def _score_papers_with_embeddings(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        min_relevance_score: float,
        min_quality_score: float,
    ) -> List[Dict[str, Any]]:
        if not papers:
            return []

        paper_texts = [f"{p['title']}\n\n{p['summary']}" for p in papers]
        vectors = self._embed_texts([query] + paper_texts)

        if len(vectors) != len(papers) + 1:
            logger.warning("[ResearchDigest] Embedding size mismatch, falling back to lexical scoring")
            return self._score_papers_lexical(
                query,
                papers,
                min_relevance_score=min_relevance_score,
                min_quality_score=min_quality_score,
            )

        query_vec = vectors[0]
        scored: List[Dict[str, Any]] = []

        for idx, paper in enumerate(papers, start=1):
            relevance = self._cosine_similarity(query_vec, vectors[idx])
            length_score = min(len(paper.get("summary", "")) / 1800.0, 1.0)
            recency_score = self._recency_score(paper.get("published", ""))
            quality = (0.75 * relevance) + (0.15 * length_score) + (0.10 * recency_score)
            high_quality = relevance >= min_relevance_score and quality >= min_quality_score

            scored.append(
                {
                    **paper,
                    "relevance_score": round(relevance, 4),
                    "quality_score": round(quality, 4),
                    "high_quality": high_quality,
                }
            )

        return sorted(scored, key=lambda p: (p["quality_score"], p["relevance_score"]), reverse=True)

    def _score_papers_lexical(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        min_relevance_score: float,
        min_quality_score: float,
    ) -> List[Dict[str, Any]]:
        query_terms = set(self._extract_keywords(query))
        scored: List[Dict[str, Any]] = []
        for paper in papers:
            text_terms = set(self._extract_keywords(f"{paper['title']} {paper['summary']}"))
            overlap = len(query_terms.intersection(text_terms))
            denom = max(len(query_terms), 1)
            relevance = min(overlap / denom, 1.0)
            length_score = min(len(paper.get("summary", "")) / 1800.0, 1.0)
            recency_score = self._recency_score(paper.get("published", ""))
            quality = (0.75 * relevance) + (0.15 * length_score) + (0.10 * recency_score)
            scored.append(
                {
                    **paper,
                    "relevance_score": round(relevance, 4),
                    "quality_score": round(quality, 4),
                    "high_quality": relevance >= min_relevance_score and quality >= min_quality_score,
                }
            )
        return sorted(scored, key=lambda p: (p["quality_score"], p["relevance_score"]), reverse=True)

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        response = self.embedding_client.embeddings.create(
            model=settings.LITELLM_EMBEDDING_MODEL,
            input=texts,
        )
        return [d.embedding for d in response.data]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        a_norm = math.sqrt(sum(x * x for x in a))
        b_norm = math.sqrt(sum(y * y for y in b))
        if a_norm == 0.0 or b_norm == 0.0:
            return 0.0

        # Normalize to [0, 1] for easier thresholding.
        cosine = dot / (a_norm * b_norm)
        return max(0.0, min((cosine + 1.0) / 2.0, 1.0))

    @staticmethod
    def _recency_score(published_iso: str) -> float:
        try:
            published_dt = datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
            years_old = max((datetime.now(timezone.utc) - published_dt).days / 365.25, 0.0)
            return max(0.0, 1.0 - (years_old / 10.0))
        except Exception:
            return 0.5

    def _analyze_single_paper(self, query: str, paper: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "You are a Research Analyst AI Agent. Analyze this arXiv paper for the given query. "
            "Return STRICT JSON with keys exactly: "
            "problem_statement, key_contributions, methodology, results, limitations, summary. "
            "Rules: summary must be <= 100 words; key_contributions must be an array of strings; "
            "results and limitations can be concise but specific; do not include markdown or code fences.\n\n"
            f"Query: {query}\n"
            f"Title: {paper['title']}\n"
            f"Abstract: {paper['summary']}\n"
            f"Authors: {', '.join(paper.get('authors', []))}\n"
            f"Published: {paper.get('published', '')}\n"
            f"Categories: {', '.join(paper.get('categories', []))}"
        )

        content = self.llm.invoke(prompt).content
        parsed = self._safe_json_parse(content)

        return {
            "title": paper["title"],
            "paper_url": paper["url"],
            "published": paper.get("published"),
            "authors": paper.get("authors", []),
            "relevance_score": paper.get("relevance_score", 0.0),
            "quality_score": paper.get("quality_score", 0.0),
            "high_quality": paper.get("high_quality", False),
            "problem_statement": parsed.get("problem_statement") or "Not clearly stated in abstract.",
            "key_contributions": parsed.get("key_contributions") if isinstance(parsed.get("key_contributions"), list) else [],
            "methodology": parsed.get("methodology") or "Methodology details are limited in abstract-level metadata.",
            "results": parsed.get("results") or "Results are summarized at abstract level.",
            "limitations": parsed.get("limitations") or "Limitations not fully explicit in abstract-level metadata.",
            "summary": self._truncate_words(parsed.get("summary") or paper.get("summary", ""), 100),
        }

    def _build_consolidated_digest(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        keyword_clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not papers:
            return {
                "consolidated_research_digest": "No relevant papers were analyzed.",
                "trends": [],
                "conflicting_ideas": [],
            }

        prompt = (
            "You are a Research Analyst AI Agent. Create a consolidated digest from analyzed papers. "
            "Return STRICT JSON with keys exactly: consolidated_research_digest, trends, conflicting_ideas. "
            "Rules: trends and conflicting_ideas must be arrays of short strings; "
            "if no conflicts, return an empty array; no markdown.\n\n"
            f"Query: {query}\n"
            f"Analyzed Papers JSON: {json.dumps(papers, ensure_ascii=False)}\n"
            f"Keyword Clusters JSON: {json.dumps(keyword_clusters, ensure_ascii=False)}"
        )

        content = self.llm.invoke(prompt).content
        parsed = self._safe_json_parse(content)

        return {
            "consolidated_research_digest": parsed.get("consolidated_research_digest")
            or "A consolidated digest could not be generated.",
            "trends": parsed.get("trends") if isinstance(parsed.get("trends"), list) else [],
            "conflicting_ideas": parsed.get("conflicting_ideas") if isinstance(parsed.get("conflicting_ideas"), list) else [],
        }

    def _render_digest_text(self, payload: Dict[str, Any]) -> str:
        """Create markdown-rich digest text for direct UI rendering."""
        lines: List[str] = []
        lines.append("## Research Digest Agent")
        lines.append("")
        lines.append(f"**Topic:** {payload.get('query', '')}")
        lines.append(f"**Decision:** {payload.get('decision', '')}")
        lines.append(f"**Reason:** {payload.get('reason', '')}")
        lines.append(
            f"**Evidence:** {payload.get('high_quality_papers_found', 0)}/{payload.get('min_required_high_quality_papers', 5)} high-quality papers"
        )
        lines.append("")

        consolidated = payload.get("consolidated_research_digest", "")
        if consolidated:
            lines.append("### Consolidated Digest")
            lines.append(consolidated)
            lines.append("")

        trends = payload.get("trends", []) or []
        if trends:
            lines.append("### Cross-Paper Trends")
            for trend in trends:
                lines.append(f"- {trend}")
            lines.append("")

        conflicts = payload.get("conflicting_ideas", []) or []
        if conflicts:
            lines.append("### Conflicting Ideas")
            for conflict in conflicts:
                lines.append(f"- {conflict}")
            lines.append("")

        papers = payload.get("papers", []) or []
        if papers:
            lines.append("### Paper Insights")
            for idx, paper in enumerate(papers, start=1):
                lines.append(f"#### {idx}. {paper.get('title', 'Untitled')}")
                lines.append(f"**Problem Statement:** {paper.get('problem_statement', '')}")
                contributions = paper.get("key_contributions", []) or []
                if contributions:
                    lines.append("**Key Contributions:**")
                    for item in contributions[:3]:
                        lines.append(f"- {item}")
                lines.append(f"**Methodology:** {paper.get('methodology', '')}")
                lines.append(f"**Results:** {paper.get('results', '')}")
                lines.append(f"**Limitations:** {paper.get('limitations', '')}")
                lines.append(f"**Summary:** {paper.get('summary', '')}")
                lines.append("")

        lines.append(f"**Next Action:** {payload.get('next_action', '')}")
        return "\n".join(lines).strip()

    def _cluster_keywords(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build simple keyword clusters based on cross-paper co-occurrence."""

        keyword_to_papers: Dict[str, set[int]] = {}

        for idx, paper in enumerate(papers):
            combined_text = " ".join(
                [
                    paper.get("title", ""),
                    paper.get("problem_statement", ""),
                    paper.get("methodology", ""),
                    " ".join(paper.get("key_contributions", [])),
                    paper.get("summary", ""),
                ]
            )
            keywords = self._extract_keywords(combined_text)[:15]
            for kw in keywords:
                keyword_to_papers.setdefault(kw, set()).add(idx)

        if not keyword_to_papers:
            return []

        ranked_terms = sorted(keyword_to_papers.keys(), key=lambda t: len(keyword_to_papers[t]), reverse=True)
        used: set[str] = set()
        clusters: List[Dict[str, Any]] = []

        for term in ranked_terms:
            if term in used:
                continue

            base_docs = keyword_to_papers[term]
            related = [term]

            for other in ranked_terms:
                if other == term or other in used:
                    continue
                docs = keyword_to_papers[other]
                overlap = len(base_docs.intersection(docs))
                if overlap == 0:
                    continue
                union = len(base_docs.union(docs))
                jaccard = overlap / union if union else 0.0
                if jaccard >= 0.34 or overlap >= 2:
                    related.append(other)
                if len(related) >= 6:
                    break

            for kw in related:
                used.add(kw)

            paper_union = set()
            for kw in related:
                paper_union.update(keyword_to_papers.get(kw, set()))

            clusters.append(
                {
                    "cluster_label": term,
                    "keywords": related,
                    "paper_count": len(paper_union),
                }
            )

            if len(clusters) >= 8:
                break

        return clusters

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {
            "the", "and", "for", "that", "with", "this", "from", "have", "using", "used", "into", "between",
            "their", "these", "those", "such", "than", "then", "also", "into", "based", "paper", "study",
            "results", "method", "methods", "approach", "analysis", "model", "models", "data", "research",
            "show", "shows", "new", "our", "are", "was", "were", "can", "not", "but", "has", "had", "its",
            "via", "over", "under", "within", "about", "across", "more", "most", "less", "many", "much",
        }
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
        filtered = [t for t in tokens if t not in stop_words and not t.isdigit()]

        freq: Dict[str, int] = {}
        for token in filtered:
            freq[token] = freq.get(token, 0) + 1

        return [term for term, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)]

    @staticmethod
    def _truncate_words(text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]).strip() + "..."

    @staticmethod
    def _safe_json_parse(raw_text: Any) -> Dict[str, Any]:
        if not isinstance(raw_text, str):
            return {}

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}


_research_digest_service: ResearchDigestService | None = None


def get_research_digest_service() -> ResearchDigestService:
    global _research_digest_service
    if _research_digest_service is None:
        _research_digest_service = ResearchDigestService()
    return _research_digest_service
