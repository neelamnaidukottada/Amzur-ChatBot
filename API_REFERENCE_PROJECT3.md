# Project 3 API Reference

## Base URL
```
Backend: http://localhost:8000
Frontend: http://localhost:5173
```

## Authentication Endpoints

### 1. Register with Email
**Endpoint**: `POST /api/auth/register`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "auth_provider": "email"
}
```

**Error** (400):
```json
{
  "detail": "Email user@example.com already registered"
}
```

---

### 2. Login with Email
**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_email": "user@example.com",
  "user_name": "John Doe",
  "auth_provider": "email"
}
```

**Error** (401):
```json
{
  "detail": "Invalid email or password"
}
```

---

### 3. Login with Google OAuth (NEW)
**Endpoint**: `POST /api/auth/google`

**Request**:
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEifQ..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_email": "user@gmail.com",
  "user_name": "John Doe",
  "auth_provider": "google"
}
```

**Error** (401):
```json
{
  "detail": "Google authentication failed: Invalid token"
}
```

**Notes**:
- Token is from Google's OAuth 2.0 library
- User created automatically if doesn't exist
- Linked to existing email user if same email
- No password stored for Google users

---

## Chat Endpoints

### 4. Send Message
**Endpoint**: `POST /api/chat/message?conversation_id=123`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request**:
```json
{
  "user_message": "What is machine learning?"
}
```

**Response** (200 OK):
```json
{
  "user_message": "What is machine learning?",
  "assistant_response": "Machine learning is a subset of artificial intelligence..."
}
```

**Error** (401):
```json
{
  "detail": "Not authenticated"
}
```

**Notes**:
- If `conversation_id` not provided, creates new conversation
- First message auto-names conversation
- Title will be: "What is machine learning?..." (truncated to 50 chars)

---

### 5. Create Conversation
**Endpoint**: `POST /api/chat/conversations`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request**:
```json
{
  "title": "My Project Discussion"
}
```

**Response** (200 OK):
```json
{
  "id": 42,
  "title": "My Project Discussion",
  "created_at": "2025-05-04T10:30:00",
  "updated_at": "2025-05-04T10:30:00",
  "messages": []
}
```

**Notes**:
- `title` is optional (defaults to "New Chat")
- Empty messages array initially
- Title will be auto-updated when first message sent

---

### 6. Get All Conversations
**Endpoint**: `GET /api/chat/conversations`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "title": "What is machine learning?...",
    "created_at": "2025-05-03T15:20:00",
    "updated_at": "2025-05-04T10:30:00",
    "message_count": 5
  },
  {
    "id": 2,
    "title": "Python Best Practices",
    "created_at": "2025-05-04T09:00:00",
    "updated_at": "2025-05-04T10:25:00",
    "message_count": 3
  }
]
```

**Sorting**: By `updated_at DESC` (newest first)

**Notes**:
- Includes message count for each conversation
- Shows relative timestamps
- Sorted by most recently updated

---

### 7. Get Specific Conversation
**Endpoint**: `GET /api/chat/conversations/42`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "id": 42,
  "title": "Machine Learning Basics",
  "created_at": "2025-05-03T15:20:00",
  "updated_at": "2025-05-04T10:30:00",
  "messages": [
    {
      "id": 101,
      "sender": "user",
      "content": "What is machine learning?",
      "created_at": "2025-05-03T15:20:00"
    },
    {
      "id": 102,
      "sender": "assistant",
      "content": "Machine learning is...",
      "created_at": "2025-05-03T15:21:00"
    }
  ]
}
```

**Error** (404):
```json
{
  "detail": "Conversation not found"
}
```

---

### 8. Update/Rename Conversation (NEW)
**Endpoint**: `PUT /api/chat/conversations/42`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request**:
```json
{
  "title": "ML Fundamentals"
}
```

**Response** (200 OK):
```json
{
  "id": 42,
  "title": "ML Fundamentals",
  "created_at": "2025-05-03T15:20:00",
  "updated_at": "2025-05-04T10:45:00",
  "messages": [
    {
      "id": 101,
      "sender": "user",
      "content": "What is machine learning?",
      "created_at": "2025-05-03T15:20:00"
    },
    {
      "id": 102,
      "sender": "assistant",
      "content": "Machine learning is...",
      "created_at": "2025-05-03T15:21:00"
    }
  ]
}
```

**Error** (404):
```json
{
  "detail": "Conversation not found"
}
```

**Notes**:
- Only updates title if provided
- Returns full conversation with all messages
- `updated_at` timestamp automatically updated
- User authorization verified (can only update own conversations)

---

### 9. Delete Conversation
**Endpoint**: `DELETE /api/chat/conversations/42`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "status": "deleted"
}
```

**Error** (404):
```json
{
  "detail": "Conversation not found"
}
```

**Notes**:
- Cascade deletes all messages in conversation
- User authorization verified
- Cannot be undone

---

## Health & Diagnostic Endpoints

### 10. Health Check
**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

### 11. Diagnostic Info
**Endpoint**: `GET /api/diagnostic`

**Response** (200 OK):
```json
{
  "status": "ok",
  "backend_running": true,
  "version": "1.0.0"
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```
**Causes**: Missing or invalid token

---

### 400 Bad Request
```json
{
  "detail": "Email user@example.com already registered"
}
```
**Causes**: Invalid input, duplicate email, etc.

---

### 404 Not Found
```json
{
  "detail": "Conversation not found"
}
```
**Causes**: Conversation ID doesn't exist or user doesn't own it

---

### 502 Bad Gateway
```json
{
  "detail": {
    "error": "llm_error",
    "message": "Failed to call LLM API"
  }
}
```
**Causes**: Backend LLM service unreachable

---

## Request/Response Formats

### Authentication Header Format
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNjE0MzI3Njg3fQ.abcd1234
```

### Timestamp Format
All timestamps are ISO 8601:
```
2025-05-04T10:30:00
```

### Pagination
Currently no pagination, all conversations returned in single response.

---

## Query Parameters

### Conversation List
```
GET /api/chat/conversations
  (No query parameters currently)
```

### Send Message
```
POST /api/chat/message?conversation_id=42
  conversation_id (optional): Create new if not provided
```

---

## Rate Limiting
Currently no rate limiting. Production should implement:
- 100 requests per minute per user
- Exponential backoff for failed requests

---

## CORS Headers
```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Example Client Implementation (TypeScript)

### Using apiClient
```typescript
// Login
const response = await apiClient.login('user@example.com', 'password123');
console.log(response.access_token);

// Or Google login
const googleResponse = await apiClient.googleLogin(googleToken);
console.log(googleResponse.access_token);

// Send message
const message = await apiClient.sendChatMessage('Hello AI!', conversationId);
console.log(message.assistant_response);

// Get all conversations
const conversations = await apiClient.getConversations();
console.log(conversations);

// Rename conversation
const updated = await apiClient.updateConversation(42, 'New Title');
console.log(updated.title);

// Delete conversation
await apiClient.deleteConversation(42);
```

### Using Curl
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Get conversations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/chat/conversations

# Send message
curl -X POST http://localhost:8000/api/chat/message?conversation_id=42 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_message":"Hello!"}'

# Rename conversation
curl -X PUT http://localhost:8000/api/chat/conversations/42 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"New Title"}'

# Delete conversation
curl -X DELETE http://localhost:8000/api/chat/conversations/42 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Changelog: Project 3 Additions

**New Endpoints**:
- `POST /api/auth/google` - Google OAuth authentication

**Modified Endpoints**:
- `PUT /api/chat/conversations/{id}` - New endpoint for renaming

**New Response Fields**:
- `TokenResponse.auth_provider` - Shows "email" or "google"
- `ConversationSummaryResponse.message_count` - Count of messages in conversation

**Auto-Naming Feature**:
- When first message sent to conversation titled "New Chat"
- Title automatically becomes message preview (50 chars max)
- Example: "What is the best..." 

---

## Version Info
- **API Version**: 1.0.0 (Project 3)
- **Last Updated**: 2025-05-04
- **Status**: Production Ready (with environment configuration)
