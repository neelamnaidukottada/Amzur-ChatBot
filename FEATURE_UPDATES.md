# Feature Updates - Chat Bot

## Overview
Three major features have been implemented to enhance the chat bot UI and functionality.

---

## 1. ✅ File Upload with Prompts

### What's New:
- **Attach Multiple Files**: Click the "+" menu → "Add photos & files" to select multiple files (images, PDFs, documents)
- **Visual File Display**: Attached files appear as cards at the top of the input area with file type icons (🖼️ for images, 📄 for documents)
- **Remove Files**: Click the ✕ button on any file card to remove it before sending
- **Send with Prompt**: Add a prompt/message along with files and send everything together
- **Smart Placeholder**: Input placeholder changes to "Add a prompt for your files..." when files are attached

### Usage:
1. Click **+** button in the input bar
2. Select **"Add photos & files"**
3. Choose files from your computer
4. Type your prompt or question about the files
5. Click **➤** to send files + prompt to AI

---

## 2. ✅ Advanced Voice Recording

### What's New:
- **Fallback Support**: Works in all browsers (Chrome, Firefox, Safari, Edge)
- **Web Speech API**: Primary method for speech-to-text (Chrome, Safari, Edge)
- **Audio Recording Fallback**: Uses MediaRecorder API if Web Speech API is not available
- **Visual Feedback**:
  - 🎙️ Mic button turns red when recording
  - Pulsing animation shows active recording
  - Recording timer shows elapsed seconds
  - Status message below input: "🎤 Recording... (Xs) Click the mic button to stop"
- **Auto-append**: Spoken text automatically appends to your input

### Usage:
1. Click **🎙️** button to start recording
2. Speak naturally
3. Click **🎙️** again (now shows ⏹️) to stop
4. Text appears in input field
5. Add more text if needed
6. Click **➤** to send

---

## 3. ✅ Folder Organization (Project Management)

### What's New:
- **Pre-built Folders**: Default folders included: "Projects", "Personal", "Work"
- **Create Folders**: Click **"+ New Folder"** button to create custom folders
- **Rename Folders**: Hover over folder → click ✎ icon → edit name
- **Delete Folders**: Hover over folder → click ✕ icon
- **Toggle Folders**: Click folder name or icon (📁/📂) to expand/collapse
- **Organize Conversations**: Each folder contains related conversations
- **Visual Hierarchy**: Conversations nested under folders with indentation and visual separators

### Usage:
1. **Create a Folder**:
   - Click **"+ New Folder"** at the bottom of the sidebar
   - Enter folder name
   - Press Enter or click ✓

2. **Manage Folders**:
   - Hover over any folder to see action buttons
   - Click folder icon to expand/collapse
   - Edit name or delete using action buttons

3. **Organize Conversations**:
   - Create new chat within a folder
   - Conversations automatically appear in the folder
   - Use rename/delete on individual conversations

---

## File Changes

### Modified Files:
1. **`frontend/src/components/InputBar.tsx`**
   - Added file attachment handling
   - Improved voice recording with fallback support
   - Enhanced menu system with all options
   - File preview display

2. **`frontend/src/components/ChatPage.tsx`**
   - Added folder management system
   - Updated sidebar with folder hierarchy
   - Added folder CRUD operations
   - Integration with file upload handler

3. **`frontend/src/lib/useAuthenticatedChat.ts`**
   - Updated sendMessage to accept files
   - Added file upload logic
   - Improved message formatting for files

4. **`frontend/src/lib/api.ts`**
   - Added sendChatMessageWithFiles method
   - Proper FormData handling for multipart uploads

---

## Technical Details

### Voice Recording:
- Primary: Web Speech API (webkitSpeechRecognition)
- Fallback: MediaRecorder API (getUserMedia)
- Supported in: Chrome, Firefox, Safari, Edge

### File Upload:
- Supported formats: images, PDF, DOC, DOCX, TXT, XLSX
- Multiple files supported
- FormData for multipart requests

### Folder System:
- Client-side state management using React hooks
- Persistent folder list (can be extended with backend storage)
- Pre-populated with 3 default folders

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Voice Recording | ✅ Web Speech | ⚠️ Fallback | ✅ Web Speech | ✅ Web Speech |
| File Upload | ✅ | ✅ | ✅ | ✅ |
| Folder Management | ✅ | ✅ | ✅ | ✅ |

---

## Next Steps (Optional Backend Integration)

To fully enable file processing on the backend:

1. Update `/api/chat/message` endpoint to accept multipart/form-data
2. Implement file processing logic in backend
3. Store file metadata with conversations
4. Add persistent folder storage to database

---

## Notes

- All changes are frontend-only and don't require backend modifications for basic functionality
- Voice recording requests microphone permission (will prompt user)
- File uploads are sent directly with chat messages (no separate storage)
- Folder management is currently client-side (refresh will reset folders)
