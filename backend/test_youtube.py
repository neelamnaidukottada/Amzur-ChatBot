#!/usr/bin/env python
"""Test YouTube transcript fetching"""

from app.services.url_service import URLService

print("Testing YouTube URL: https://youtu.be/i3dsHKzJ2oE")
result = URLService.process_url_or_video('https://youtu.be/i3dsHKzJ2oE')

print(f"\nResult:")
print(f"  Success: {result['success']}")
print(f"  Type: {result.get('source_type')}")
print(f"  Error: {result.get('error', 'None')}")

if result.get('content'):
    print(f"  Content length: {len(result['content'])} chars")
    print(f"  Content preview:\n{result['content'][:300]}")
else:
    print(f"  No content returned")
