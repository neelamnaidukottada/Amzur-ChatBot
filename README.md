# Amzur Simple Chatbot with Authentication & Chat History

A conversational AI chatbot built with authentication, chat history persistence, and a modern UI.

**Stack:**
- **Backend:** FastAPI, Python, LangChain, SQLAlchemy, PostgreSQL
- **Frontend:** React 18, TypeScript, Tailwind CSS, React Router
- **LLM Gateway:** Amzur LiteLLM Proxy
- **Auth:** JWT tokens with bcrypt password hashing

## Features

- ✅ **User Authentication** - Secure login/registration with JWT tokens
- ✅ **Chat History** - Store and load all conversations from database
- ✅ **Conversation Management** - Create, view, delete, and organize chats
- ✅ **Persistent Messages** - All messages are saved in PostgreSQL
- ✅ **Protected Routes** - Frontend routes require authentication
- ✅ **Modern UI** - Responsive design with sidebar navigation
- ✅ **Natural Language SQL (Project 8)** - Connect a SQL DB and ask questions using `/db <database-url> | <question>`

## Prerequisites

- **Python 3.9+** (Backend)
- **Node.js 18+** (Frontend)
- **PostgreSQL 12+** (Database)

## Backend Setup

### 1. Database Setup

First, create a PostgreSQL database:

```bash
# Using psql or your preferred PostgreSQL client
createdb chatbot_db
```

Or using PostgreSQL GUI tool, create a database named `chatbot_db`.

### 2. Python Environment

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
source venv/Scripts/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database - Update with your PostgreSQL credentials
DATABASE_URL=postgresql://username:password@localhost:5432/chatbot_db

# LiteLLM Proxy (Amzur)
LITELLM_PROXY_URL=https://litellm.amzur.com
LITELLM_API_KEY=sk-your-actual-api-key
LLM_MODEL=gpt-4o

# JWT Configuration (change SECRET_KEY in production)
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_NAME=amzur-simple-chatbot
ENVIRONMENT=development
```

### 5. Initialize Database

The database tables are automatically created when you start the backend (via `init_db()` in `main.py`). 

To manually initialize:

```bash
python -c "from app.core.init_db import init_db; init_db(); print('Database initialized!')"
```

### 6. Run Backend Server

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## Frontend Setup

### 1. Navigate to Frontend

In a new terminal:

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Run Development Server

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 4. Access Application

Open your browser to: `http://localhost:5173`

You'll be redirected to the login page. Create an account or login with existing credentials.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── chat.py           # Chat endpoints (messages, conversations)
│   │   └── auth.py           # Authentication endpoints (login, register)
│   ├── services/
│   │   ├── chat_service.py   # Chat business logic
│   │   ├── auth_service.py   # Authentication service
│   │   └── conversation_service.py  # Conversation management
│   ├── schemas/
│   │   ├── chat.py           # Chat request/response schemas
│   │   ├── auth.py           # Auth request/response schemas
│   │   └── conversation.py   # Conversation schemas
│   ├── core/
│   │   ├── models.py         # SQLAlchemy database models
│   │   ├── database.py       # Database connection
│   │   ├── auth.py           # JWT and password utilities
│   │   ├── settings.py       # Configuration management
│   │   └── init_db.py        # Database initialization
│   ├── ai/
│   │   └── llm.py            # LangChain LLM client
│   └── main.py               # FastAPI application
├── requirements.txt          # Python dependencies
└── .env.example              # Example environment file

frontend/
├── src/
│   ├── components/
│   │   ├── ChatPage.tsx      # Main chat interface with sidebar
│   │   ├── LoginPage.tsx     # Login/register page
│   │   ├── MessageList.tsx   # Message display component
│   │   └── InputBar.tsx      # Message input component
│   ├── lib/
│   │   ├── api.ts            # API client (auth, chat, conversations)
│   │   ├── useChat.ts        # Legacy chat hook
│   │   └── useAuthenticatedChat.ts  # New auth chat hook
│   ├── types/
│   │   ├── chat.ts           # TypeScript interfaces
│   │   └── index.ts          # Export types
│   ├── App.tsx               # Main app with routing
│   ├── main.tsx              # React entry point
│   └── index.css             # Tailwind styles
├── package.json              # NPM dependencies
└── vite.config.ts            # Vite configuration
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "full_name": "John Doe"
  }
  ```

- `POST /api/auth/login` - Login user
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```

### Chat Messages

- `POST /api/chat/message` - Send message (authenticated)
  ```json
  {
    "user_message": "Hello, how are you?"
  }
  ```

### Conversations

- `POST /api/chat/conversations` - Create new conversation
  ```json
  {
    "title": "Project Discussion"
  }
  ```

- `GET /api/chat/conversations` - Get all conversations

- `GET /api/chat/conversations/{id}` - Get specific conversation with messages

- `DELETE /api/chat/conversations/{id}` - Delete conversation

## Authentication Flow

1. **User Registration/Login** 
   - User enters email and password on login page
   - Backend validates credentials and returns JWT token
   - Token is stored in browser localStorage

2. **Protected Routes**
   - Frontend checks for token before rendering chat page
   - All API requests include token in `Authorization: Bearer <token>` header
   - Backend validates token and returns 401 if invalid

3. **Chat History**
   - When user sends a message, backend creates/uses current conversation
   - Messages are saved to database with timestamp
   - Users can view all their previous conversations from sidebar

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(255),
  hashed_password VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Conversations Table
```sql
CREATE TABLE conversations (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) DEFAULT 'New Chat',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Messages Table
```sql
CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  sender VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Testing

### Test User Registration
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
  }'
```

### Test User Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Test Chat Message (requires token)
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "user_message": "Hello!"
  }'
```

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env file
- Verify PostgreSQL credentials
- Ensure chatbot_db database exists

### Backend Won't Start
- Check all environment variables are set in .env
- Ensure port 8000 is not in use
- Run `pip install -r requirements.txt` again
- Check Python version is 3.9+

### Frontend Login Issues
- Clear browser localStorage and cache
- Check backend is running on port 8000
- Check CORS is enabled
- Open browser DevTools (F12) to see errors

### Conversations Not Loading
- Ensure user is authenticated
- Check token is valid and not expired
- Verify conversations exist in database
- Check database connection

## Development Tips

- **Backend API Docs:** Visit `http://localhost:8000/docs` for Swagger UI
- **Database Explorer:** Use pgAdmin or `psql` command-line tool
- **Frontend Debugging:** Use React DevTools browser extension
- **API Logging:** Backend logs all requests and errors to console

## Production Deployment

Before deploying:

1. **Security:**
   - Generate a strong SECRET_KEY for JWT
   - Use environment variables for all secrets
   - Enable HTTPS
   - Set ENVIRONMENT=production

2. **Database:**
   - Use managed PostgreSQL (e.g., AWS RDS)
   - Enable SSL connections
   - Set up regular backups

3. **Backend:**
   - Use production ASGI server (gunicorn + uvicorn)
   - Set DEBUG=False
   - Configure proper logging

4. **Frontend:**
   - Run `npm run build`
   - Serve from CDN or static hosting
   - Update VITE_API_URL environment variable

## License

This project is part of the Amzur Chatbot initiative.
4. **Components** - MessageList and InputBar handle UI rendering

## Key Features

- ✅ Simple, clean chat interface
- ✅ Real-time message streaming
- ✅ LangChain LCEL chain architecture
- ✅ All AI calls routed through Amzur LiteLLM
- ✅ TypeScript strict mode
- ✅ Tailwind CSS styling
- ✅ Error handling

## Environment Variables

### Backend (.env)
```
LITELLM_PROXY_URL=https://litellm.amzur.com
LITELLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4o
APP_NAME=amzur-simple-chatbot
ENVIRONMENT=development
```

### Frontend (.env, if needed)
```
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### "Connection refused" when backend starts
- Ensure VPN is connected (LiteLLM proxy is internal-only)
- Run `nslookup litellm.amzur.com` to verify DNS resolution

### "Cannot find module 'langchain_openai'"
- Install `langchain-openai`: `pip install langchain-openai`

### Frontend shows "Failed to send message"
- Verify backend is running on `http://localhost:8000`
- Check browser console for detailed error messages
- Ensure CORS is properly configured

## Next Steps

To extend this chatbot:
- Add conversation memory/history
- Implement user authentication
- Add support for file uploads (images, PDFs)
- Add markdown rendering for responses
- Implement streaming responses
- Add database persistence
