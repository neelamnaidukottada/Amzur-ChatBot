"""RAG service for PDF ingestion and retrieval using ChromaDB."""

from __future__ import annotations

import logging
import os
import uuid
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.settings import settings
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class RAGService:
    """Manage PDF indexing and retrieval for chat conversations."""

    def __init__(self) -> None:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        self.embeddings = OpenAIEmbeddings(
            model=settings.LITELLM_EMBEDDING_MODEL,
            api_key=settings.LITELLM_API_KEY,
            base_url=settings.LITELLM_PROXY_URL,
        )
        self.vectorstore = Chroma(
            collection_name="conversation_pdf_chunks",
            persist_directory=settings.CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )

    def ingest_pdf(
        self,
        file_content: bytes,
        filename: str,
        user_id: int,
        conversation_id: int,
    ) -> int:
        """Extract, split, embed, and store PDF chunks for retrieval."""
        extracted_text = FileService.extract_text_from_file(
            file_content=file_content,
            filename=filename,
            content_type="application/pdf",
        )

        if not extracted_text:
            raise ValueError(f"Unable to extract PDF text from {filename}")

        extraction_error_markers = (
            "[Error reading PDF file:",
            "[PDF support not available",
            "[No text found in PDF]",
        )
        if extracted_text.startswith(extraction_error_markers):
            raise ValueError(f"Unable to extract PDF text from {filename}")

        chunks = self.text_splitter.split_text(extracted_text)
        if not chunks:
            raise ValueError(f"No indexable text chunks found in {filename}")

        docs: List[Document] = []
        ids: List[str] = []
        for index, chunk in enumerate(chunks):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "filename": filename,
                        "chunk_index": str(index),
                        "user_id": str(user_id),
                        "conversation_id": str(conversation_id),
                    },
                )
            )
            ids.append(str(uuid.uuid4()))

        self.vectorstore.add_documents(documents=docs, ids=ids)
        logger.info(
            "[RAGService] Indexed %s chunks for file=%s user_id=%s conversation_id=%s",
            len(docs),
            filename,
            user_id,
            conversation_id,
        )
        return len(docs)

    def retrieve_context(
        self,
        query: str,
        user_id: int,
        conversation_id: int,
        k: int = 5,
    ) -> str:
        """Retrieve top-k relevant chunks for a query."""
        if not query.strip():
            return ""

        filter_by_conversation = {
            "$and": [
                {"user_id": {"$eq": str(user_id)}},
                {"conversation_id": {"$eq": str(conversation_id)}},
            ]
        }
        docs = self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter_by_conversation,
        )

        if not docs:
            docs = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter={"user_id": {"$eq": str(user_id)}},
            )

        if not docs:
            return ""

        formatted_chunks = []
        for idx, doc in enumerate(docs, start=1):
            filename = doc.metadata.get("filename", "unknown.pdf")
            chunk_index = doc.metadata.get("chunk_index", "?")
            formatted_chunks.append(
                f"[Source {idx}] file={filename}, chunk={chunk_index}\n{doc.page_content}"
            )

        return "\n\n".join(formatted_chunks)


_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Get singleton RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
