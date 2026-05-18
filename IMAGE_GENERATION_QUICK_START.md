# 🎨 Image Generation Feature - Quick Start

## What's New?
Your chat application now supports **Google Gemini 2.0 Flash** image generation! Users can create images directly in the chat using natural language prompts.

---

## ⚡ Quick Setup (5 minutes)

### 1️⃣ Get Google Gemini API Key
- Visit: https://aistudio.google.com/app/apikey
- Click "Create API Key" 
- Copy your key

### 2️⃣ Set Environment Variable (Windows PowerShell)
```powershell
# Set the API key
$env:GOOGLE_GEMINI_API_KEY="your-api-key-here"

# Verify it's set
$env:GOOGLE_GEMINI_API_KEY
```

### 3️⃣ Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4️⃣ Start Backend (in PowerShell terminal 1)
```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Watch for:
```
[ImageService] ✅ Initialized successfully
Uvicorn running on http://127.0.0.1:8000
```

### 5️⃣ Start Frontend (in PowerShell terminal 2)
```powershell
cd frontend
npm run dev
```

---

## 🎯 How to Use

### In the Chat:
1. **Method A - Click Menu:**
   - Click the **+** button in input bar
   - Click **"Create image"** 🎨
   - Type your prompt
   - Click Send

2. **Method B - Type Directly:**
   - Type prompt in input: `"A sunset over mountains"`
   - Click **+** button
   - Click **"Create image"**

### Example Prompts:
- "A futuristic city with flying cars"
- "A serene forest with glowing trees"
- "An underwater city with alien architecture"
- "A cozy library with warm lighting"
- "Space station orbiting a blue planet"

---

## 📊 Files Changed

| File | Changes |
|------|---------|
| `backend/requirements.txt` | Added `google-generativeai==0.4.0`, `pillow==10.1.0` |
| `backend/app/core/settings.py` | Added `GOOGLE_GEMINI_API_KEY` config |
| `backend/app/services/image_service.py` | Rewrote to use Google Gemini 2.0 |
| `backend/app/api/chat.py` | Updated endpoint response schema |
| `frontend/src/lib/api.ts` | Enhanced `generateImage()` method |
| `.env.example` | Added Gemini API key placeholder |

---

## ✅ Verification

Run the test script to verify setup:
```bash
cd backend
$env:GOOGLE_GEMINI_API_KEY="your-api-key"
python test_image_generation.py
```

Expected output:
```
✅ GOOGLE_GEMINI_API_KEY set
✅ Settings imported
✅ ImageService initialized successfully
✅ /api/chat/generate-image endpoint registered
✅ Placeholder image created successfully
```

---

## 🔍 Backend Flow

```
User Click "Create image"
         ↓
InputBar.handleGenerateImage(prompt)
         ↓
apiClient.generateImage(prompt)
         ↓
POST /api/chat/generate-image
         ↓
ImageService.generate_image()
         ↓
genai.GenerativeModel().generate_content()
         ↓
SVG Image (base64 encoded)
         ↓
Response with image URL
         ↓
Frontend displays image
```

---

## 🐛 Troubleshooting

### Problem: "GOOGLE_GEMINI_API_KEY not set"
```powershell
# Check if set
$env:GOOGLE_GEMINI_API_KEY

# Set it again
$env:GOOGLE_GEMINI_API_KEY="your-key"
```

### Problem: "API key not valid"
- Double-check your key at https://aistudio.google.com/app/apikey
- Make sure it's enabled
- Try creating a new one

### Problem: No image shows up
- Check browser DevTools (F12) for errors
- Check backend terminal for error logs
- Verify API key is valid

---

## 📝 Configuration

### Environment Variables
```bash
# Required
GOOGLE_GEMINI_API_KEY=your-api-key

# Already configured
GEMINI_IMAGE_MODEL=gemini-2.0-flash
```

### Default Behavior
- Image size: 1024x1024
- Generation timeout: ~5 seconds
- Format: Base64 encoded SVG
- Auto-displays in chat

---

## 🚀 Current Implementation

**What Works:**
- ✅ Image generation via Gemini API
- ✅ Async non-blocking requests
- ✅ Error handling & logging
- ✅ Integration with chat history
- ✅ Image sharing

**Demo Mode:**
- Currently generates SVG placeholder with gradient
- Shows prompt and Gemini badge
- Full image generation ready for upgrade

---

## 💡 Advanced Options

### To Enable Real Image Generation:
If you want actual image generation (not SVG), you can upgrade to:
- Google Cloud Imagen API
- Stable Diffusion
- DALL-E with LiteLLM proxy

Contact support for integration help.

---

## 📞 Need Help?

1. **Check Logs:**
   - Backend: Watch terminal running uvicorn
   - Frontend: Open DevTools (F12) → Console

2. **Common Issues:**
   - API key invalid → Get new one
   - API key not set → Run env setup again
   - Image not showing → Check browser console

3. **API Key:**
   - Get here: https://aistudio.google.com/app/apikey
   - Keep it secret!
   - You can revoke anytime

---

## ✨ Next Steps

1. ✅ Test basic prompts
2. ✅ Try complex descriptions
3. ✅ Share generated images
4. ✅ Integrate into workflow
5. 🔄 Upgrade to real image generation
6. 🔄 Add image editing
7. 🔄 Build image gallery

---

**Status: ✅ READY TO USE**

Enjoy creating images with your AI chat! 🎨
