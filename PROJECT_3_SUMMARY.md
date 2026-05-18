# Project 3: Google OAuth & Advanced Thread Management

## Overview
Extended the Amzur Chatbot with Google OAuth login, advanced conversation management, and auto-naming for chat threads. Users can now authenticate via Google and manage their conversations with renamed threads that load automatically upon login.

## Features Implemented

### 1. Google OAuth Login ✅
- **Backend**: Added Google OAuth token verification using `google-auth` library
- **Frontend**: Integrated Google Sign-In button with `@react-oauth/google`
- **Database**: Extended User model with `google_id`, `google_email`, and `auth_provider` fields
- **Account Linking**: Automatically links Google accounts to existing email-based accounts
- **New Endpoint**: `POST /api/auth/google` - Authenticates user via Google OAuth token

### 2. Chat Thread Management ✅
- **Create**: Users can create new conversations (threads) - auto-named from first message
- **Read**: View all conversations in chronological order (newest first)
- **Update**: 
  - Auto-name: First user message becomes the thread title
  - Manual rename: Edit conversation titles via UI
  - New endpoint: `PUT /api/chat/conversations/{id}` for updating titles
- **Delete**: Remove conversations with confirmation dialog

### 3. Auto-Naming Threads ✅
- **Implementation**: `ConversationService.generate_title_from_message()` 
- **Behavior**: 
  - Takes first 50 characters of first user message
  - Handles multi-line messages (uses first line)
  - Adds ellipsis if truncated
  - Falls back to "New Chat" if empty
- **Trigger**: Automatically when first message is added to new conversation

### 4. Thread Loading on Login ✅
- **Implementation**: `useAuthenticatedChat` hook loads all conversations on mount
- **Behavior**: 
  - Fetches conversations sorted by `updated_at DESC` (newest first)
  - Shows message count per conversation
  - Displays relative timestamps (e.g., "5 minutes ago")
- **UI**: Sidebar displays all user's threads with latest activity

### 5. Frontend Conversation Rename UI ✅
- **Rename Icon**: Edit button (✎) next to each conversation
- **Inline Editing**: Click rename to enter edit mode
- **Quick Actions**: 
  - ✓ (checkmark) to save
  - ✕ (X) to cancel
- **Delete Icon**: ✕ button for deletion with confirmation

## Technical Implementation

### Backend Changes

#### 1. Models (`app/core/models.py`)
```python
class User:
    # New OAuth fields
    hashed_password: Optional[str]  # Nullable for OAuth-only users
    google_id: Optional[str]        # Google unique identifier
    google_email: Optional[str]     # Email from Google
    auth_provider: str              # 'email' or 'google'
```

#### 2. Settings (`app/core/settings.py`)
```python
GOOGLE_CLIENT_ID: str       # From environment
GOOGLE_CLIENT_SECRET: str   # From environment
```

#### 3. Auth Service (`app/services/auth_service.py`)
```python
# New method: authenticate_google_user(db, token)
# - Verifies Google token
# - Creates or links user account
# - Returns User object
```

#### 4. Conversation Service (`app/services/conversation_service.py`)
```python
# New method: generate_title_from_message(message, max_length=50)
# - Extracts first line from message
# - Truncates to 50 characters
# - Adds "..." if truncated
# - Returns sanitized title

# Modified: add_message()
# - Auto-generates title from first user message
# - Updates title only if currently "New Chat"
```

#### 5. API Endpoints
```
POST /api/auth/google
  Request:  { token: "<Google JWT>" }
  Response: { access_token, token_type, user_email, user_name, auth_provider }
  
PUT /api/chat/conversations/{id}
  Request:  { title: "New Title" }
  Response: ConversationResponse (full conversation object)
```

### Frontend Changes

#### 1. API Client (`src/lib/api.ts`)
```typescript
// New methods:
async googleLogin(token: string)                          // POST /api/auth/google
async updateConversation(id: number, title: string)       // PUT /api/chat/conversations/{id}
```

#### 2. Login Component (`src/components/LoginPage.tsx`)
- Added GoogleLogin button
- Divider between OAuth and email login
- Google token handling with `CredentialResponse`
- Error handling for Google authentication

#### 3. Chat Hook (`src/lib/useAuthenticatedChat.ts`)
```typescript
// New method:
async renameConversation(id: number, newTitle: string)
```

#### 4. Chat Page (`src/components/ChatPage.tsx`)
- Rename mode toggle for each conversation
- Edit (✎) and Delete (✕) buttons
- Inline text input for renaming
- Save (✓) and Cancel (✕) actions during edit
- Conversation selection clears rename mode

### Configuration

#### Backend `.env` Setup
```env
# Google OAuth (optional for now)
GOOGLE_CLIENT_ID=<your_google_client_id>
GOOGLE_CLIENT_SECRET=<your_google_client_secret>

# Existing settings
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

#### Frontend `.env.local` Setup
```env
VITE_GOOGLE_CLIENT_ID=<your_google_client_id>
VITE_API_URL=http://localhost:8000
```

## User Flow

### 1. First-Time Google Login
```
User clicks "Sign in with Google" 
  ↓
Selects Google account
  ↓
Backend verifies token
  ↓
Creates new User with google_id + auth_provider='google'
  ↓
Returns JWT token
  ↓
User logged in and redirected to chat
```

### 2. Auto-Naming Thread
```
User creates new conversation (empty "New Chat")
  ↓
User sends first message: "What is machine learning?"
  ↓
Backend adds message and checks title
  ↓
Title "New Chat" → generates "What is machine learning?..."
  ↓
ConversationService.generate_title_from_message() runs
  ↓
Title updated to "What is machine learning" (50 chars max)
  ↓
Frontend shows updated title in sidebar
```

### 3. Manual Thread Rename
```
User clicks edit icon (✎) on conversation
  ↓
Input field appears with current title
  ↓
User types new title
  ↓
User clicks save (✓) or cancels (✕)
  ↓
PUT /api/chat/conversations/{id} called if saving
  ↓
Sidebar and current conversation updated
```

### 4. Login and Load Threads
```
User logs in successfully
  ↓
Redirected to ChatPage
  ↓
useAuthenticatedChat hook mounted
  ↓
GET /api/chat/conversations fetched
  ↓
Sidebar populated with all user's threads
  ↓
Sorted by updated_at DESC (newest first)
  ↓
Message count shown per thread
```

## Database Schema Changes

### User Table (Extended)
```sql
ALTER TABLE users 
ADD COLUMN hashed_password VARCHAR(255) NULL,
ADD COLUMN google_id VARCHAR(255) UNIQUE NULL,
ADD COLUMN google_email VARCHAR(255) NULL,
ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'email';
```

**Notes:**
- `hashed_password` made nullable for OAuth-only users
- `google_id` has unique index for fast lookups
- `auth_provider` tracks which authentication method was used

### Conversation Table (No Changes)
- Existing schema unchanged
- Auto-naming handled in application layer
- Title field supports up to 255 characters

## Security Considerations

### Google OAuth
1. **Token Verification**: Uses `google.auth.transport.requests.Request()`
2. **Client ID Validation**: Verifies token was issued for our client
3. **Claims Extraction**: Safely extracts `sub` (user ID), `email`, `name`

### Password Security
- Email-based users still use bcrypt (no changes)
- OAuth users have `NULL` password (no password attacks possible)
- Password verification checks `if user.hashed_password` first

### Account Linking
- Email match triggers linking (requires user confirmation in production)
- Both auth methods can access same account
- `auth_provider` field tracks primary method

## Testing Checklist

### Backend Tests
- [ ] Register new email user
- [ ] Login with email user
- [ ] Google OAuth token verification (with mock token)
- [ ] Create conversation with auto-naming
- [ ] Rename conversation via PUT endpoint
- [ ] Delete conversation
- [ ] Load all conversations for user

### Frontend Tests
- [ ] Google Sign-In button visible
- [ ] Google login redirects to chat
- [ ] Email login still works
- [ ] New conversations auto-name from first message
- [ ] Conversations load on page refresh
- [ ] Rename conversation inline
- [ ] Delete conversation with confirmation
- [ ] Logout clears token and redirects

### End-to-End Tests
1. Register with email + send message → auto-named
2. Logout and login again → see saved conversation
3. Rename conversation → updates in sidebar
4. Create multiple conversations → ordered by newest first
5. Google login → creates new account or links existing

## Dependencies Added

### Backend (`requirements.txt`)
- `google-auth==2.26.1` - OAuth 2.0 token verification
- `google-auth-httplib2==0.2.0` - HTTP transport for Google Auth
- `google-auth-oauthlib==1.1.0` - OAuth library support

### Frontend (`package.json`)
- `@react-oauth/google==0.12.1` - Google Sign-In React component

## Known Limitations & Future Enhancements

### Current Limitations
1. No email verification for new accounts
2. Google account linking automatic (no confirmation)
3. Limited to Google OAuth (no GitHub, Microsoft, etc.)
4. Auto-naming based only on first message
5. No conversation sharing between users

### Future Enhancements
1. Add more OAuth providers (GitHub, Microsoft, Apple)
2. Email verification flow
3. Account linking confirmation dialog
4. Smart naming using LLM for better summaries
5. Conversation search and filtering
6. Bulk conversation management
7. Export conversation as PDF/Markdown
8. Conversation templates

## Troubleshooting

### Google Login Not Working
1. **Check Client ID**: Verify `VITE_GOOGLE_CLIENT_ID` in `.env.local`
2. **CORS Issues**: Ensure frontend domain in Google Cloud Console
3. **Token Expiration**: Frontend token valid for 1 hour default
4. **Backend Token Verification**: Check `GOOGLE_CLIENT_ID` in `.env`

### Conversations Not Loading
1. **Check Auth**: Verify `auth_token` in localStorage
2. **Backend Running**: Ensure `http://localhost:8000` accessible
3. **Database**: Verify conversations exist in `conversations` table
4. **API Response**: Check browser DevTools Network tab

### Auto-Naming Not Working
1. **First Message Check**: Title only auto-named on first user message
2. **Title "New Chat"**: Only replaces if currently "New Chat"
3. **Message Storage**: Verify message stored before title updated
4. **Database Commit**: Check transactions committed properly

## Summary
Project 3 successfully extends the application with enterprise-grade authentication and advanced conversation management, enabling seamless user experience with multiple login options and intelligent thread organization.
