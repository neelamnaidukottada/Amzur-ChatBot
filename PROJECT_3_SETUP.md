# Project 3 Setup Guide: Google OAuth & Thread Management

## Prerequisites
- Both backend and frontend running
- Supabase PostgreSQL database configured
- Google Cloud Console account

## Step 1: Get Google OAuth Credentials

### 1.1 Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Create Project**
3. Enter project name: `Amzur Chatbot`
4. Click **Create**

### 1.2 Enable OAuth API
1. Go to **APIs & Services** → **Library**
2. Search for `Google Identity Services`
3. Click **Google Identity Services**
4. Click **Enable**

### 1.3 Create OAuth 2.0 Credentials
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure OAuth consent screen first:
   - User Type: **External**
   - Click **Create**
   - Fill in app name: `Amzur Chatbot`
   - Click **Save and Continue**
   - Click **Save and Continue** again (skip optional scopes)
   - Click **Save and Continue** (test users)
   - Click **Back to Dashboard**

4. Now create OAuth client ID:
   - Application type: **Web application**
   - Name: `Amzur Chatbot Web`
   - Authorized JavaScript origins:
     ```
     http://localhost:5173
     http://localhost:3000
     http://127.0.0.1:5173
     http://127.0.0.1:3000
     ```
   - Authorized redirect URIs:
     ```
     http://localhost:5173/
     http://localhost:3000/
     http://127.0.0.1:5173/
     http://127.0.0.1:3000/
     ```
   - Click **Create**

5. Copy your credentials:
   - **Client ID**: (save this)
   - **Client Secret**: (save this)

## Step 2: Configure Backend

### 2.1 Update `.env` File
Edit `backend/.env`:

```env
# Google OAuth
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE

# ... (keep existing settings)
DATABASE_URL=postgresql://...
SECRET_KEY=...
LLM_MODEL=gpt-4o
```

### 2.2 Restart Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

## Step 3: Configure Frontend

### 3.1 Create `.env.local` File
Create `frontend/.env.local`:

```env
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
VITE_API_URL=http://localhost:8000
```

### 3.2 Restart Frontend
```bash
cd frontend
npm run dev
```

**Expected output:**
```
➜  Local:   http://localhost:5173/
➜  press h to show help
```

## Step 4: Test Google OAuth

### 4.1 Open Login Page
1. Navigate to `http://localhost:5173`
2. You should see **Sign in with Google** button
3. Click it

### 4.2 Google Sign-In Flow
1. Select your Google account
2. Approve permissions if prompted
3. You should be logged in and redirected to chat page
4. Check sidebar - you'll see empty conversation list

## Step 5: Test Auto-Naming

### 5.1 Create New Conversation
1. Click **+ New Chat**
2. New conversation created with title "New Chat"

### 5.2 Send First Message
1. Type a message: `"What are the best practices for machine learning?"`
2. Click Send
3. Watch the title update automatically to: `"What are the best practices for machine learning?"`

### 5.3 Send More Messages
- Thread title stays the same
- Messages are stored in conversation

## Step 6: Test Thread Management

### 6.1 Rename Conversation
1. Hover over conversation in sidebar
2. Click edit icon (✎)
3. Type new title: `"ML Best Practices"`
4. Click save (✓)
5. Title updates immediately

### 6.2 Create Multiple Threads
1. Click **+ New Chat**
2. Send message: `"Explain quantum computing"`
3. Title auto-updates
4. Create 2-3 more threads
5. Verify sidebar shows all threads sorted by newest first

### 6.3 Delete Thread
1. Hover over thread in sidebar
2. Click delete (✕)
3. Confirm deletion
4. Thread removed from sidebar

## Step 7: Test Persistence

### 7.1 Refresh Page
1. In chat, press F5 (or Cmd+R)
2. You should be redirected to login (token check)
3. You stay logged in (localStorage preserves token)
4. All conversations reload in sidebar

### 7.2 New Tab
1. Open new tab: `http://localhost:5173`
2. Already logged in (shared localStorage)
3. Same conversations visible

### 7.3 Logout & Login Again
1. Click **Logout** in sidebar
2. Redirected to login page
3. Click **Sign in with Google**
4. Same account, same conversations appear

## Step 8: Email Login Still Works

### 8.1 Test Email Registration
1. Toggle to **Sign up** on login page
2. Register with:
   - Full Name: `Test User`
   - Email: `test@example.com`
   - Password: `SecurePass123`
3. Click **Create Account**
4. Logged in automatically
5. Create and send messages

### 8.2 Logout & Login with Email
1. Click **Logout**
2. Enter email and password
3. Should login successfully
4. Same conversations visible (if you used same email for Google)

## Troubleshooting

### "Sign in with Google" Button Not Showing
**Problem**: Button doesn't appear on login page

**Solutions**:
1. Check browser console for errors (DevTools F12)
2. Verify `VITE_GOOGLE_CLIENT_ID` in `.env.local`
3. Ensure frontend restarted after `.env.local` changes
4. Check that Client ID is valid (from Google Cloud Console)

### Google Login Fails with "Token Verification Failed"
**Problem**: Error after clicking Google account

**Solutions**:
1. Verify `GOOGLE_CLIENT_ID` in `backend/.env` matches frontend
2. Check backend logs for error message
3. Ensure backend has `google-auth` package installed: `pip install google-auth`
4. Restart backend after installing packages

### Conversations Not Auto-Naming
**Problem**: First message doesn't update title

**Solutions**:
1. Verify title is still "New Chat" before first message
2. Check that you're sending a **user** message, not system
3. Look at backend logs for any errors
4. Manually rename to test the rename endpoint works

### Can't Login After Google Account
**Problem**: Got error message after successful Google auth

**Solutions**:
1. Check backend logs for database errors
2. Verify PostgreSQL is running and connected
3. Check `DATABASE_URL` is correct in `.env`
4. Restart backend and try again

### Threads Not Loading After Login
**Problem**: Sidebar empty or conversations don't load

**Solutions**:
1. Check browser console (DevTools) for errors
2. Check backend is running: `http://localhost:8000/health`
3. Verify token in localStorage (DevTools → Application → Local Storage)
4. Check network requests (DevTools → Network → XHR)

## Database Changes

After running with Google OAuth, your `users` table will have:
- `auth_provider` column showing `'google'` or `'email'`
- `google_id` column populated for Google users
- `google_email` column populated for Google users
- `hashed_password` NULL for Google-only users

**To view in Supabase:**
1. Go to Supabase Dashboard
2. Click **SQL Editor**
3. Run query:
   ```sql
   SELECT id, email, auth_provider, google_id FROM users;
   ```

## Project 3 Features Summary

✅ **Google OAuth Login** - Sign in with Google account
✅ **Auto-Naming Threads** - First message becomes thread title
✅ **Thread Rename** - Edit conversation titles inline
✅ **Thread Management** - Create, read, update, delete conversations
✅ **Persistence** - All conversations load on login
✅ **Account Linking** - Google account links to email accounts

## Next Steps

1. **Configure in Production**: Update Google OAuth URLs to production domain
2. **Email Verification**: Add email confirmation flow
3. **More Providers**: Add GitHub, Microsoft OAuth
4. **LLM Naming**: Use AI to generate smarter thread titles
5. **Sharing**: Allow sharing conversations with other users

## Support

For issues, check:
- Backend logs: `python -m uvicorn app.main:app --reload` output
- Frontend logs: Browser DevTools Console (F12)
- Network requests: DevTools → Network tab
- Database: Supabase SQL Editor
