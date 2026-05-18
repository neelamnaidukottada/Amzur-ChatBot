# Quick Start: Project 3 Features

## Prerequisites
✅ Python 3.10+ installed  
✅ Node.js 16+ installed  
✅ Supabase PostgreSQL configured  
✅ Google OAuth credentials (optional - email login works without it)

## Setup (First Time Only)

### 1. Backend Setup
```bash
cd backend

# Install dependencies (includes google-auth)
pip install -r requirements.txt

# Create .env file with your settings
echo "DATABASE_URL=postgresql://..." > .env
echo "SECRET_KEY=your-secret-key" >> .env
echo "GOOGLE_CLIENT_ID=your_client_id" >> .env  # Optional
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies (includes @react-oauth/google)
npm install

# Create .env.local file
echo "VITE_GOOGLE_CLIENT_ID=your_client_id" > .env.local
echo "VITE_API_URL=http://localhost:8000" >> .env.local
```

## Running the Application

### Terminal 1: Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```
Expected: `Local: http://localhost:5173/`

## Testing Project 3 Features

### Option 1: Google OAuth Login (Recommended)
1. Open `http://localhost:5173`
2. Click **"Sign in with Google"**
3. Select your Google account
4. Redirected to chat page ✅

### Option 2: Email Login (Works Without Google Setup)
1. Click **"Sign up"** toggle
2. Enter:
   - Full Name: `Test User`
   - Email: `test@example.com`
   - Password: `SecurePass123`
3. Click **"Create Account"** ✅

## Feature Checklist

### Auto-Naming Threads
- [ ] Start new chat (title: "New Chat")
- [ ] Send message: "What is artificial intelligence?"
- [ ] Title updates to: "What is artificial intelligence?..." ✅

### Rename Conversations
- [ ] Hover over conversation in sidebar
- [ ] Click edit icon ✎
- [ ] Type new title: "AI Basics"
- [ ] Click save ✓ ✅

### Delete Conversations
- [ ] Hover over conversation in sidebar
- [ ] Click delete icon ✕
- [ ] Confirm deletion
- [ ] Conversation removed ✅

### Persistence
- [ ] Create 2-3 conversations with messages
- [ ] Refresh page (F5)
- [ ] All conversations appear in sidebar ✅
- [ ] Click logout and login again
- [ ] Same conversations still there ✅

## API Endpoints (Project 3 New)

### Authentication
```
POST /api/auth/google
  Payload: { token: "<Google JWT token>" }
  Returns: { access_token, user_email, auth_provider: "google" }
```

### Conversation Management
```
PUT /api/chat/conversations/{id}
  Payload: { title: "New Title" }
  Returns: Full Conversation object
```

## Troubleshooting

### "Can't connect to backend"
- Check backend running: `http://localhost:8000/health` → should return `{"status":"ok"}`
- Check CORS: Ensure `http://localhost:5173` in `ALLOWED_ORIGINS`

### Google login button missing
- Verify `VITE_GOOGLE_CLIENT_ID` set in `frontend/.env.local`
- Restart frontend: `npm run dev`
- Check browser console for errors

### Auto-naming not working
- Verify title is "New Chat" before sending first message
- Check backend logs for errors
- Try manual rename to test PUT endpoint

### Conversations don't load
- Check token in localStorage (DevTools → Application)
- Verify database connection: `DATABASE_URL` in `.env`
- Check network requests in DevTools → Network tab

## Database Check

To view created users and conversations in Supabase:
```sql
-- View users
SELECT id, email, auth_provider, created_at FROM users;

-- View conversations
SELECT c.id, c.title, c.user_id, COUNT(m.id) as message_count 
FROM conversations c 
LEFT JOIN messages m ON c.id = m.conversation_id 
GROUP BY c.id;
```

## File Structure (Project 3)

```
Experiment-Chat-Bot/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── models.py          ← User: added google_id, auth_provider
│   │   │   ├── auth.py
│   │   │   └── settings.py        ← Added GOOGLE_CLIENT_ID
│   │   ├── services/
│   │   │   ├── auth_service.py    ← Added authenticate_google_user()
│   │   │   └── conversation_service.py  ← Added generate_title_from_message()
│   │   ├── api/
│   │   │   ├── auth.py            ← Added POST /api/auth/google
│   │   │   └── chat.py            ← Added PUT /api/chat/conversations/{id}
│   │   └── schemas/
│   │       └── auth.py            ← Added GoogleLoginRequest
│   ├── requirements.txt           ← Added google-auth packages
│   └── .env                       ← Set GOOGLE_CLIENT_ID
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage.tsx      ← Added Google login button
│   │   │   └── ChatPage.tsx       ← Added rename UI
│   │   ├── lib/
│   │   │   ├── api.ts            ← Added googleLogin(), updateConversation()
│   │   │   └── useAuthenticatedChat.ts  ← Added renameConversation()
│   │   ├── main.tsx              ← Wrapped with GoogleOAuthProvider
│   │   └── App.tsx
│   ├── package.json              ← Added @react-oauth/google
│   └── .env.local                ← Set VITE_GOOGLE_CLIENT_ID
│
├── PROJECT_3_SUMMARY.md          ← Full feature documentation
└── PROJECT_3_SETUP.md            ← Google OAuth setup guide
```

## Next Commands

```bash
# View backend logs
tail -f backend.log

# View frontend compilation errors  
npm run dev

# Run backend tests (if tests added)
pytest backend/tests/

# Format code
black backend/
prettier --write frontend/src
```

## Success Indicators ✅

- Backend running without errors
- Frontend loading at `http://localhost:5173`
- Google or email login working
- Chat page displaying conversations
- First message auto-names thread
- Rename feature working
- All conversations persist after refresh
