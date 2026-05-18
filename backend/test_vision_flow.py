#!/usr/bin/env python
"""Test the updated vision LLM flow using native google-generativeai"""

import os
import sys
import base64
from io import BytesIO
from PIL import Image

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# Import after path setup
import google.generativeai as genai
from app.core.settings import settings

def test_vision_flow():
    """Test that vision LLM can analyze images"""
    try:
        print("[*] Testing Vision LLM flow with native Gemini API...")
        
        # Configure Gemini
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        print("[*] Gemini model configured")
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Encode to base64
        image_bytes = img_byte_arr.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"[*] Created test image, encoded to base64: {len(image_base64)} chars")
        
        # Send to Gemini
        print("[*] Sending image to Gemini for analysis...")
        
        response = model.generate_content([
            "What color is this image? Be brief.",
            {
                "mime_type": "image/png",
                "data": image_base64
            }
        ])
        
        print(f"[✓] Vision LLM Response: {response.text}")
        print("[✓] Vision flow test PASSED!")
        
    except Exception as e:
        print(f"[✗] Vision flow test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_vision_flow()
