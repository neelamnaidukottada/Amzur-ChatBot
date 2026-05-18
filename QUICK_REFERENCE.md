# Quick Reference Guide

## Starting the Application

### Terminal 1 - Backend
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m uvicorn app.main:app --reload
```
Backend: http://localhost:8000
Docs: http://localhost:8000/docs

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```
Frontend: http://localhost:5173

## Common Commands

### Database
```bash
# Connect to database
psql -d chatbot_db

# View tables
\dt

# View users
SELECT * FROM users;

# View conversations for user
SELECT * FROM conversations WHERE user_id = 1;

# View messages in conversation
SELECT * FROM messages WHERE conversation_id = 1;

# Delete all data (reset database)
DROP TABLE messages, conversations, users CASCADE;
```

### Backend
```bash
# Install new package
pip install package_name

# Update requirements
pip freeze > requirements.txt

# Run migrations (future)
alembic upgrade head

# Test API endpoint
curl http://localhost:8000/health
```

### Frontend
```bash
# Install new package
npm install package-name

# Build for production
npm run build

# Preview production build
npm run preview

# Clean cache
rm -rf node_modules
npm install
```

## Authentication

### Get JWT Token
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response includes access_token
```

### Use Token in Requests
```bash
curl -X GET http://localhost:8000/api/chat/conversations \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Clear Auth in Frontend
```javascript
// In browser console
localStorage.clear()
location.reload()
```

## File Organization

### Backend Structure
```
app/
├── api/              # HTTP endpoints
│   ├── auth.py       # Auth routes
│   └── chat.py       # Chat routes
├── services/         # Business logic
│   ├── auth_service.py
│   ├── chat_service.py
│   └── conversation_service.py
├── core/             # Configuration
│   ├── models.py     # Database models
│   ├── database.py   # DB connection
│   ├── auth.py       # JWT utilities
│   ├── settings.py   # Environment vars
│   └── init_db.py    # DB initialization
├── schemas/          # Pydantic models
│   ├── auth.py
│   ├── chat.py
│   └── conversation.py
└── main.py           # App entry point
```

### Frontend Structure
```
src/
├── components/       # React components
│   ├── LoginPage.tsx
│   ├── ChatPage.tsx
│   ├── MessageList.tsx
│   └── InputBar.tsx
├── lib/              # Utilities
│   ├── api.ts        # API client
│   └── useAuthenticatedChat.ts
├── types/            # TypeScript
│   └── chat.ts
├── App.tsx           # Router
└── main.tsx          # Entry point
```

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
LITELLM_API_KEY=sk-xxx
LITELLM_PROXY_URL=https://litellm.amzur.com
LLM_MODEL=gpt-4o
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_NAME=amzur-simple-chatbot
ENVIRONMENT=development
```

### Frontend (.env, optional)
```env
VITE_API_URL=http://localhost:8000
```

## API Endpoints Quick Reference

### Auth
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/register` | Create new user |
| POST | `/api/auth/login` | Get JWT token |

### Chat (all require auth header)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/chat/message` | Send message |
| POST | `/api/chat/conversations` | Create conversation |
| GET | `/api/chat/conversations` | List conversations |
| GET | `/api/chat/conversations/{id}` | Get conversation |
| DELETE | `/api/chat/conversations/{id}` | Delete conversation |

## Common Issues

| Issue | Solution |
|-------|----------|
| Port 8000 in use | `netstat -ano \| findstr :8000` then kill PID |
| Port 5173 in use | `lsof -i :5173` then kill PID |
| Database connection error | Check DATABASE_URL, ensure PostgreSQL running |
| Login not working | Clear localStorage, check credentials |
| 401 Unauthorized | Token expired or missing, re-login |
| CORS error | Backend CORS settings, check allowed origins |
| Messages not saving | Check conversation_id, verify database connection |

## Git Workflow

```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "feat: add authentication"

# Push
git push origin main

# Pull latest
git pull origin main
```

## Code Style

### Backend (Python)
- Follow PEP 8
- Type hints on all functions
- Docstrings on all classes/functions
- 100 char line limit

### Frontend (TypeScript)
- Use TypeScript, no `any` types
- Functional components with hooks
- Clear component names
- Prop interfaces defined

## Adding New Features

### Example: Add new endpoint

1. **Create schema** in `app/schemas/`
   ```python
   class NewRequest(BaseModel):
       field: str
   ```

2. **Add to service** in `app/services/`
   ```python
   def new_function():
       pass
   ```

3. **Create endpoint** in `app/api/`
   ```python
   @router.post("/new")
   async def new_endpoint(req: NewRequest, ...):
       pass
   ```

4. **Add API client method** in `src/lib/api.ts`
   ```typescript
   async newFunction() {
       return this.client.post('/api/new', data);
   }
   ```

5. **Use in component**
   ```typescript
   const result = await apiClient.newFunction();
   ```

## Debugging

### Backend Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
logger.error("Error")
```

### Frontend Logging
```javascript
console.log("Debug", variable);
console.error("Error", error);
```

### Database Inspection
```bash
psql -d chatbot_db
\dt                    # List tables
SELECT * FROM users;   # View data
\d users               # Describe table
```

## Performance Tips

1. **Database:**
   - Use indexes on foreign keys
   - Batch queries when possible
   - Use pagination for large result sets

2. **Backend:**
   - Cache frequently accessed data
   - Use async operations
   - Implement connection pooling

3. **Frontend:**
   - Memoize expensive computations
   - Lazy load components
   - Optimize API calls

## Security Reminders

- 🔒 Never commit `.env` file
- 🔒 Change SECRET_KEY for production
- 🔒 Use HTTPS in production
- 🔒 Keep dependencies updated
- 🔒 Validate all user inputs
- 🔒 Use parameterized queries (SQLAlchemy does this)
- 🔒 Implement rate limiting

## Testing Checklist

- [ ] User can register
- [ ] User can login
- [ ] User can send message
- [ ] Message appears in chat
- [ ] Conversation saves to database
- [ ] User can view conversation history
- [ ] User can delete conversation
- [ ] User can logout
- [ ] Token refresh works (if implemented)
- [ ] Error messages display correctly

---

**Happy coding! 🚀**
