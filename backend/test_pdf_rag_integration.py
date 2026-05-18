"""One-command integration test for PDF upload + RAG retrieval flow."""

from __future__ import annotations

import argparse
import io
import json
import random
import string
import sys
import time

import requests
from reportlab.pdfgen import canvas


def _build_test_pdf(secret_code: str) -> bytes:
    """Create a small PDF in memory with a deterministic secret code."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, f"Integration Test PDF: Launch code is {secret_code}.")
    pdf.drawString(72, 730, "This file is used to verify RAG retrieval from ChromaDB.")
    pdf.save()
    return buffer.getvalue()


def _random_suffix(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _require_ok(response: requests.Response, label: str) -> None:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed: {response.status_code} {response.text}")


def run(base_url: str, timeout_sec: int, expected_code: str) -> None:
    email = f"pdf-rag-test-{int(time.time())}-{_random_suffix()}@example.com"
    password = "SecurePass123"

    print("[1/5] Register test user")
    register = requests.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": password, "full_name": "PDF RAG Test"},
        timeout=timeout_sec,
    )
    if register.status_code not in (200, 400):
        _require_ok(register, "Register")

    print("[2/5] Login and get JWT")
    login = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=timeout_sec,
    )
    _require_ok(login, "Login")
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("[3/5] Upload PDF in chat (indexes into ChromaDB)")
    pdf_bytes = _build_test_pdf(expected_code)
    upload = requests.post(
        f"{base_url}/api/chat/message",
        headers=headers,
        data={"user_message": "I uploaded a PDF. Please read and remember it."},
        files={"files": ("integration_test.pdf", pdf_bytes, "application/pdf")},
        timeout=timeout_sec,
    )
    _require_ok(upload, "PDF upload chat")

    conversations = requests.get(
        f"{base_url}/api/chat/conversations",
        headers=headers,
        timeout=timeout_sec,
    )
    _require_ok(conversations, "List conversations")
    conversation_list = conversations.json()
    if not conversation_list:
        raise RuntimeError("No conversation found after upload")
    conversation_id = conversation_list[0]["id"]

    print("[4/5] Ask retrieval question in same conversation")
    query = "What is the launch code from the uploaded PDF? Reply with only the code."
    question = requests.post(
        f"{base_url}/api/chat/message",
        params={"conversation_id": conversation_id},
        headers={**headers, "Content-Type": "application/json"},
        json={"user_message": query},
        timeout=timeout_sec,
    )
    _require_ok(question, "RAG retrieval question")
    assistant_response = question.json().get("assistant_response", "")

    print("[5/5] Assert expected answer")
    passed = expected_code in assistant_response
    result = {
        "pass": passed,
        "expected_code": expected_code,
        "conversation_id": conversation_id,
        "assistant_response": assistant_response,
    }
    print(json.dumps(result, indent=2))

    if not passed:
        raise RuntimeError("RAG integration assertion failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PDF RAG integration test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=120, help="Request timeout in seconds")
    parser.add_argument("--code", default="ALPHA-7319", help="Expected code to embed and verify")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(base_url=args.base_url.rstrip("/"), timeout_sec=args.timeout, expected_code=args.code)
        print("PASS: PDF RAG integration test succeeded")
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
