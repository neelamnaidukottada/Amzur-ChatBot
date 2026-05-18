#!/usr/bin/env python
"""Quick test to verify FileService works"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.file_service import FileService

# Test 1: TXT file
print("=" * 60)
print("TEST 1: TXT FILE")
print("=" * 60)
txt_content = b"This is a test text file with some content. It has multiple lines. And we want to extract all of it."
result = FileService.extract_text_from_file(txt_content, "test.txt", "text/plain")
print(f"Result type: {type(result)}")
print(f"Result length: {len(str(result)) if result else 0} chars")
print(f"Result preview: {str(result)[:200] if result else 'EMPTY/None'}")
print(f"✅ PASS" if result and len(str(result).strip()) > 0 else "❌ FAIL")

# Test 2: Empty file
print("\n" + "=" * 60)
print("TEST 2: EMPTY FILE")
print("=" * 60)
empty_content = b""
result = FileService.extract_text_from_file(empty_content, "empty.txt", "text/plain")
print(f"Result: {result}")
print(f"✅ PASS" if result else "❌ FAIL")

# Test 3: Unsupported file type
print("\n" + "=" * 60)
print("TEST 3: UNSUPPORTED FILE TYPE")
print("=" * 60)
result = FileService.extract_text_from_file(b"xyz", "file.xyz", "application/xyz")
print(f"Result: {result}")
print(f"✅ PASS" if result else "❌ FAIL")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
