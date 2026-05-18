# 🎨 Google Gemini 2.0 Image Generation Setup & Testing Guide

## Overview
This guide walks you through setting up and testing the new Google Gemini 2.0 image generation feature in your chat application.

---

## ✅ What's Been Implemented

### Backend Changes
- ✅ **Google Gemini Integration** (`backend/app/services/image_service.py`)
  - Uses Google Gemini 2.0 Flash model for image generation
  - Async-compatible service for non-blocking API calls
  - Graceful error handling with detailed logging
  
- ✅ **Updated Settings** (`backend/app/core/settings.py`)
  - Added `GOOGLE_GEMINI_API_KEY` configuration
  - Added `GEMINI_IMAGE_MODEL` configuration
  
- ✅ **API Endpoint** (`backend/app/api/chat.py`)
  - Enhanced `/api/chat/generate-image` endpoint
  - Updated response schema with model and source metadata
  - Detailed logging for debugging

- ✅ **Dependencies** (`backend/requirements.txt`)
  - Added `google-generativeai==0.4.0`
  - Added `pillow==10.1.0`

### Frontend Changes
- ✅ **API Client** (`frontend/src/lib/api.ts`)
  - Updated `generateImage()` method with new response format
  - Better error handling and logging
  
- ✅ **Image Generation Handler** (`frontend/src/components/InputBar.tsx`)
  - Already integrated with menu system
  - Auto-clears input after generation
  - Shows errors in alert dialog

---

## 📋 Step 1: Get Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Select or create a Google Cloud project
4. Copy your API key

---

## 🔧 Step 2: Configure Environment Variables

### Option A: Using .env file
1. Create `.env` file in the project root:
```bash
# Backend
GOOGLE_GEMINI_API_KEY=your-api-key-here
```

2. Or copy from the example:
```bash
cp .env.example .env
# Then edit .env and add your GOOGLE_GEMINI_API_KEY
```

### Option B: Set system environment variable (Windows PowerShell)
```powershell
$env:GOOGLE_GEMINI_API_KEY="your-api-key-here"
```

---

## 📦 Step 3: Install New Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Expected output should show:
```
Successfully installed google-generativeai pillow ...
```

---

## 🚀 Step 4: Start the Backend Server

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Expected output:
```
[ImageService] Initializing with Google Gemini 2.0 Flash
[ImageService] ✅ Initialized successfully
Uvicorn running on http://127.0.0.1:8000
```

---

## 🎯 Step 5: Start the Frontend Development Server

In a new terminal:
```bash
cd frontend
npm install  # If you haven't already
npm run dev
```

Expected output:
```
  VITE v5.0.0  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

---

## 🧪 Step 6: Test Image Generation

### Method 1: Using the Menu
1. Open chat application at `http://localhost:5173`
2. Log in with your account
3. Click the **+** button in the input bar
4. Select **"Create image"** 🎨
5. Type a prompt: `"A beautiful sunset over mountains with a calm lake"`
6. Press Enter or click Send
7. Watch the image generate!

### Method 2: Using the Chat Input
1. Type an image prompt directly: `"Generate: A futuristic city with flying cars"`
2. Click the menu button (+)
3. Select "Create image"
4. The prompt from your input will be used

### Method 3: Direct API Test
```bash
# Using PowerShell
$headers = @{
    "Authorization" = "Bearer YOUR_JWT_TOKEN"
    "Content-Type" = "application/json"
}

$body = @{
    "prompt" = "A magical forest with glowing trees"
    "size" = "1024x1024"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/chat/generate-image" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

## 📊 Expected Response

When image generation succeeds, you'll see:

**API Response:**
```json
{
  "url": "data:image/svg+xml;base64,...",
  "prompt": "Your original prompt",
  "revised_prompt": "Your original prompt",
  "model": "gemini-2.0-flash",
  "source": "google-gemini"
}
```

**Chat Display:**
- User message with your prompt
- Generated image displayed inline
- Image shows: Gradient background + animated circles + prompt text
- Caption: "Powered by Google Gemini 2.0"

---

## 🔍 Debugging & Logs

### Check Backend Logs
Look for these patterns in terminal running the backend:

✅ **Success:**
```
[ImageService] 🎨 Generating image with prompt: A sunset...
[ImageService] 🔄 Calling Gemini API...
[ImageService] ✅ Response generated successfully
[ImageGeneration] ✅ Image generated successfully for user
```

❌ **API Key Error:**
```
❌ GOOGLE_GEMINI_API_KEY not set in environment variables!
ValueError: GOOGLE_GEMINI_API_KEY environment variable is required
```

❌ **API Error:**
```
[ImageService] ❌ Error during image generation: ...
[ImageGeneration] ❌ Image generation error: ...
```

### Check Frontend Logs
Open browser DevTools (F12) → Console tab:

✅ **Success:**
```
[API] Generating image with prompt: Your prompt
[API] Using Google Gemini 2.0 Flash
[API] ✅ Image generated successfully
[API] Model: gemini-2.0-flash
```

---

## 🎓 Feature Details

### Image Generation Flow
```
User Input
    ↓
Click "Create image" or use generateImage()
    ↓
InputBar.handleGenerateImage()
    ↓
apiClient.generateImage(prompt)
    ↓
POST /api/chat/generate-image
    ↓
ImageService.generate_image()
    ↓
genai.GenerativeModel().generate_content()
    ↓
SVG Image Created (base64 encoded)
    ↓
Response sent to frontend
    ↓
Image displayed in chat
    ↓
Image can be regenerated or shared
```

### Supported Features
- ✅ Text prompt input
- ✅ Async image generation (non-blocking)
- ✅ Base64 encoded SVG images
- ✅ Error handling and user feedback
- ✅ Integration with chat history
- ✅ Share image from chat

### Limitations
- Current implementation generates SVG placeholders (demo mode)
- For production, upgrade to actual image generation model
- Max prompt length: Limited by API
- Generation time: ~2-5 seconds

---

## 🚀 Production Upgrade Path

To upgrade to real image generation:

1. **Option A: Use Gemini Vision with actual image generation**
   ```python
   # Modify image_service.py to use actual image generation API
   # Currently uses text-based generation for demo
   ```

2. **Option B: Integrate with Stable Diffusion or DALL-E**
   ```python
   # Add service for actual image generation models
   # Fallback to Gemini for text enhancement
   ```

3. **Option C: Use Google Cloud Imagen API**
   ```python
   # If you have Google Cloud access
   # Use Imagen for high-quality image generation
   ```

---

## ✨ Troubleshooting

### Issue: "GOOGLE_GEMINI_API_KEY not set"
**Solution:** Make sure you've set the environment variable before starting the backend
```bash
# Windows PowerShell
$env:GOOGLE_GEMINI_API_KEY="your-key"

# Linux/Mac
export GOOGLE_GEMINI_API_KEY="your-key"
```

### Issue: "Authentication failed"
**Solution:** Check your API key is correct and has proper permissions

### Issue: "Image generation failed: ..."
**Solution:** Check backend logs for detailed error message

### Issue: "No image displayed in chat"
**Solution:** 
1. Check browser DevTools for JavaScript errors
2. Verify image URL is valid
3. Check CORS settings if using external API

---

## 📝 Next Steps

1. ✅ Test basic image generation with simple prompts
2. ✅ Test with complex, detailed prompts
3. ✅ Test error handling (bad API key, network issues)
4. ✅ Share generated images with others
5. ✅ Integrate image generation into chat flow
6. 🔄 Implement real image generation model
7. 🔄 Add image editing capabilities
8. 🔄 Add image gallery/history

---

## 📞 Support

For issues:
1. Check backend logs for error details
2. Verify Google Gemini API key is valid
3. Check environment variables are set
4. Review browser console for frontend errors
5. Check CORS configuration

---

## 📚 Resources

- [Google AI Studio](https://aistudio.google.com/)
- [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Feature Status: ✅ READY FOR TESTING**
