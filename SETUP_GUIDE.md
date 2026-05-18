# Setup and Installation Guide

## Project 2: Enhanced Chatbot with PostgreSQL, Authentication & Chat History

This document provides step-by-step instructions to set up the enhanced chatbot application with database persistence, user authentication, and conversation history.

## What's New in This Enhancement

### Backend Features
- ✅ PostgreSQL database integration with SQLAlchemy ORM
- ✅ User authentication with JWT tokens
- ✅ Password hashing with bcrypt
- ✅ Conversation history storage
- ✅ Message persistence in database
- ✅ Protected API endpoints
- ✅ User profile management

### Frontend Features
- ✅ Login/Registration page with email and password
- ✅ Protected routes (redirects to login if not authenticated)
- ✅ Conversation sidebar with all previous chats
- ✅ Load existing conversations and messages
- ✅ Create new conversations
- ✅ Delete conversations
- ✅ JWT token management
- ✅ Logout functionality

## Prerequisites

Ensure you have installed:
- Python 3.9 or higher
- Node.js 18 or higher  
- PostgreSQL 12 or higher

## Installation Steps

### Step 1: Database Setup

Create a PostgreSQL database:

**Option A: Using command line**
```bash
createdb chatbot_db
```

**Option B: Using pgAdmin GUI**
1. Open pgAdmin
2. Right-click on "Databases"
3. Select "Create" → "Database"
4. Name it `chatbot_db` and click "Save"

### Step 2: Backend Setup

#### 2.1 Navigate to backend directory
```bash
cd backend
```

#### 2.2 Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 2.3 Install dependencies
```bash
pip install -r requirements.txt
```

#### 2.4 Configure environment variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings
# Windows: notepad .env
# macOS/Linux: nano .env
```

**Required .env Configuration:**
```env
# Database - Update with your PostgreSQL credentials
DATABASE_URL=postgresql://username:password@localhost:5432/chatbot_db

# LiteLLM API
LITELLM_API_KEY=sk-your-actual-api-key
LITELLM_PROXY_URL=https://litellm.amzur.com
LLM_MODEL=gpt-4o

# JWT (change SECRET_KEY in production!)
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App config
APP_NAME=amzur-simple-chatbot
ENVIRONMENT=development
```

#### 2.5 Initialize database
The database tables are created automatically when the backend starts. To verify:

```bash
python -c "from app.core.init_db import init_db; init_db(); print('✅ Database tables created!')"
```

#### 2.6 Start backend server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
Uvicorn running on http://0.0.0.0:8000
```

✅ **Backend is ready!**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Step 3: Frontend Setup

#### 3.1 In a NEW terminal, navigate to frontend
```bash
cd frontend
```

#### 3.2 Install dependencies
```bash
npm install
```

#### 3.3 Start frontend development server
```bash
npm run dev
```

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

✅ **Frontend is ready!**

### Step 4: Access the Application

1. Open browser to: **http://localhost:5173**
2. You'll see the login page
3. Click "Sign up" to create an account
4. Enter:
   - Email: `user@example.com`
   - Password: `securepassword123` (min 8 characters)
   - Full Name: `Your Name`
5. Click "Create Account"
6. You'll be logged in and can start chatting!

## Verifying Installation

### Backend Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

### Database Connection
```bash
# Connect to PostgreSQL
psql -d chatbot_db -U your_username

# View tables
\dt

# Should show: users, conversations, messages tables
```

### API Documentation
Visit: http://localhost:8000/docs

### Test Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

## Database Schema

### Users Table
Stores user account information:
- `id` - Primary key
- `email` - Unique email address
- `full_name` - User's full name
- `hashed_password` - Bcrypt hashed password
- `is_active` - Account status
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp

### Conversations Table
Stores chat conversations:
- `id` - Primary key
- `user_id` - Foreign key to users
- `title` - Conversation title (e.g., "Project Discussion")
- `created_at` - Conversation start time
- `updated_at` - Last message time

### Messages Table
Stores individual messages:
- `id` - Primary key
- `conversation_id` - Foreign key to conversations
- `sender` - "user" or "assistant"
- `content` - Message text
- `created_at` - Message timestamp

## Common Issues & Solutions

### Issue: "Cannot connect to database"
**Solution:**
1. Verify PostgreSQL is running
2. Check DATABASE_URL in .env file
3. Verify database `chatbot_db` exists
4. Check PostgreSQL credentials

### Issue: "Backend port 8000 already in use"
**Solution:**
```bash
# Kill the process using port 8000
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
# Then kill the PID
```

### Issue: "Frontend shows blank page / 404 errors"
**Solution:**
1. Check backend is running on http://localhost:8000
2. Open browser DevTools (F12) and check Console tab
3. Clear browser cache and localStorage
4. Restart both frontend and backend

### Issue: "Login fails / Invalid token"
**Solution:**
1. Clear browser localStorage: `localStorage.clear()`
2. Verify backend .env has SECRET_KEY set
3. Restart backend server
4. Try registering a new account

### Issue: "Messages don't save to database"
**Solution:**
1. Verify tables were created: `\dt` in psql
2. Check conversation_id is being passed correctly
3. Verify user_id matches in database
4. Check backend logs for errors

## Project Structure

```
Experiment-Chat-Bot/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   └── chat.py       # Chat endpoints
│   │   ├── services/         # Business logic
│   │   │   ├── auth_service.py
│   │   │   ├── chat_service.py
│   │   │   └── conversation_service.py
│   │   ├── core/             # Core functionality
│   │   │   ├── models.py     # Database models
│   │   │   ├── database.py   # DB connection
│   │   │   ├── auth.py       # JWT utilities
│   │   │   ├── settings.py   # Configuration
│   │   │   └── init_db.py    # DB initialization
│   │   ├── schemas/          # Request/response models
│   │   ├── ai/               # LLM integration
│   │   └── main.py           # FastAPI app
│   ├── requirements.txt
│   ├── .env                  # Your environment config (not in git)
│   └── .env.example          # Example config
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── LoginPage.tsx       # Login/register UI
    │   │   ├── ChatPage.tsx        # Main chat UI
    │   │   ├── MessageList.tsx
    │   │   └── InputBar.tsx
    │   ├── lib/
    │   │   ├── api.ts              # API client
    │   │   └── useAuthenticatedChat.ts  # Chat hook
    │   ├── types/
    │   │   └── chat.ts             # TypeScript types
    │   ├── App.tsx                 # App routing
    │   └── main.tsx                # React entry
    ├── package.json
    └── vite.config.ts
```

## Key Features Implementation

### Authentication Flow
1. User registers → Backend creates user with hashed password
2. Backend returns JWT token → Frontend stores in localStorage
3. Frontend adds token to all API requests
4. Backend validates token on protected routes
5. User logs out → Token is cleared from localStorage

### Chat History Flow
1. User sends message → Message stored as "user" in database
2. Backend generates response → Stored as "assistant" 
3. Both added to conversation automatically
4. User can view all previous conversations in sidebar
5. Clicking conversation loads all its messages

## Next Steps

### To Add More Features:
- Email verification
- User profiles with preferences
- Conversation sharing
- Message search
- Rate limiting
- Usage analytics
- Dark mode
- Message reactions/feedback

### To Deploy:
1. Set `ENVIRONMENT=production`
2. Generate strong SECRET_KEY
3. Use managed PostgreSQL service
4. Deploy backend to cloud (Heroku, AWS, etc.)
5. Build and deploy frontend to CDN
6. Set up SSL/HTTPS

## Support & Documentation

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Backend Logs:** Check terminal output while backend runs
- **Frontend Logs:** Check browser console (F12)
- **Database:** Use psql or pgAdmin to inspect data

## Security Notes

- ⚠️ Change SECRET_KEY before production deployment
- ⚠️ Keep LITELLM_API_KEY private
- ⚠️ Use environment variables for all secrets
- ⚠️ Enable HTTPS for production
- ⚠️ Implement rate limiting for authentication endpoints
- ⚠️ Keep dependencies updated

---

**Congratulations!** Your enhanced chatbot with authentication and chat history is now running! 🎉
