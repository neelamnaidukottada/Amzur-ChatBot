# Context Menu - Quick Visual Guide 🎯

## Where to Find It

### On Every Conversation:
```
Hover over any chat in Recents:

┌────────────────────────────┐
│ • What is LLM              │
│   2 hours ago        ⋮ ←─── Click here!
└────────────────────────────┘

⋮ button appears on hover
```

---

## Context Menu Overview

```
Click ⋮ button:

┌─────────────────────────┐
│ 📤 Share                │
├─────────────────────────┤
│ ✏️  Rename               │
├─────────────────────────┤
│ 📁 Move to project  →   │
├─────────────────────────┤
│ 📌 Pin chat             │
├─────────────────────────┤
│ 📦 Archive              │
├─────────────────────────┤
│ 🗑️  Delete              │
└─────────────────────────┘
```

---

## Each Feature Explained

### 1️⃣ **Share** 📤
```
Click "📤 Share"
   ↓
Link auto-copies:
"http://localhost:5173?chat=123"
   ↓
Alert shows link
   ↓
You can paste & share anywhere
```

### 2️⃣ **Rename** ✏️
```
Click "✏️ Rename"
   ↓
Inline edit mode activates
"What is LLM" → [input field]
   ↓
Type new name: "LLM Basics"
   ↓
Save/Enter to confirm
```

### 3️⃣ **Move to Project** 📁
```
Click "📁 Move to project" →
   ↓
Submenu shows:
  └─ Projects
  └─ Personal
  └─ Work
   ↓
Click desired folder
   ↓
Conversation added to that folder
(Also stays in Recents)
```

### 4️⃣ **Pin Chat** 📌
```
Click "📌 Pin chat"
   ↓
Conversation moves to top
   ↓
Appears with:
  📍 Icon in title
  Yellow background
   ↓
Next time, button shows "Unpin"
(Click to remove pin)
```

### 5️⃣ **Archive** 📦
```
Click "📦 Archive"
   ↓
Conversation disappears
from main Recents
   ↓
Appears in bottom section:
"📦 ARCHIVED"
   ↓
Shows grayed out (60% opacity)
   ↓
Click menu → "Unarchive" to restore
```

### 6️⃣ **Delete** 🗑️
```
Click "🗑️ Delete" (red button)
   ↓
Confirmation dialog:
"Are you sure?"
   ↓
Click "OK" to confirm
   ↓
Conversation removed permanently
   ↓
No recovery possible!
```

---

## Real-World Examples

### Example 1: Organize Work Chats
```
You have chats:
✓ Team meeting notes
✓ Project planning
✓ Random search
✓ Old research

Solution:
1. Open ⋮ for "Team meeting notes"
2. Click "Move to project" → "Work"
3. Open ⋮ for "Old research"
4. Click "Archive"

Result:
  📁 Work folder (2)
  📌 Pinned (0)
  Recents (2 - planning & random)
  📦 Archived (1 - research)
```

### Example 2: Find & Share Important Chat
```
You need to share "Python Tutorial":
1. Search Recents for it
2. Click ⋮
3. Click "Share"
4. Link copied automatically
5. Paste in Slack/Email

Friend opens link
→ See your "Python Tutorial" chat
```

### Example 3: Clean Up Recents
```
You have 20 old chats cluttering view:
1. Select each old chat
2. Click ⋮ → "Archive"
3. All archive together
4. Recents now clean!
5. Old chats still accessible below

To restore:
1. Scroll to "📦 Archived"
2. Click ⋮ → "Unarchive"
3. Returns to Recents
```

### Example 4: Create Organization System
```
Click "+ New Folder" → "Frontend"
Click "+ New Folder" → "Backend"

For each relevant chat:
1. Open ⋮
2. Click "Move to project" → select folder
3. Organize by category

Later:
📂 Frontend (5 chats)
📂 Backend (8 chats)
📂 Projects (default)
```

---

## Sidebar Organization Levels

### Level 1: Pinned (Always Visible)
```
📌 PINNED CHATS (yellow)
  • Important project ✅
  • Key decisions ✅
  • Current task ✅
```

### Level 2: Active (Scrollable)
```
💬 RECENTS
  • Latest chat
  • Recent work
  • Recent research
```

### Level 3: Organized (Folders)
```
📁 PROJECTS
  📂 Frontend (3)
  📂 Backend (5)
  📂 Work (2)
```

### Level 4: Hidden (But Accessible)
```
📦 ARCHIVED
  • Old project
  • Past research
  • Legacy notes
```

---

## Tips & Tricks

### ⚡ Quick Tips:
1. **Pin frequently used chats** for quick access
2. **Archive old chats** to clean up sidebar
3. **Move to folders** for better organization
4. **Share links** instead of copying text
5. **Use rename** to make titles searchable

### 🎯 Best Practices:
- Pin: 2-3 most important chats
- Archive: Weekly cleanup
- Organize: By project/category
- Delete: Only truly unwanted
- Share: For team collaboration

### 💡 Organization System:
```
Option A: By Time
  📁 Today
  📁 This Week
  📁 This Month

Option B: By Type
  📁 Research
  📁 Development
  📁 Admin

Option C: By Project
  📁 Project A
  📁 Project B
  📁 Personal
```

---

## Keyboard Shortcuts (Available)

| Action | Key |
|--------|-----|
| Open context menu | Right-click (future) |
| Delete | Click 🗑️ in menu |
| Quick pin | ⋮ → "Pin" |
| Quick archive | ⋮ → "Archive" |

---

## What Happens to Data

### Pin: 
- Local only (not saved to DB)
- Resets on page refresh (for now)
- Can unpin anytime

### Archive:
- Local only (not saved to DB)
- Resets on page refresh (for now)
- Can unarchive anytime

### Move to Project:
- Adds to folder conversationIds
- Conversation appears in both places
- Persists on refresh

### Delete:
- ⚠️ **Permanent removal**
- Deleted from database
- No recovery possible
- Confirmation dialog prevents accidents

### Share:
- Creates public link
- Works as long as conversation exists
- Safe to share
- Future: Could add password protection

---

## Troubleshooting

### ❌ Problem: ⋮ button not showing
**Solution:**
- Hover over chat name
- Button appears on hover
- If still not visible, refresh page

### ❌ Problem: Context menu closed
**Solution:**
- Click ⋮ again to reopen
- Menu auto-closes when clicking option
- Clicking elsewhere closes it

### ❌ Problem: Archived chat disappeared
**Solution:**
- Scroll to bottom of sidebar
- Look for "📦 ARCHIVED" section
- Click ⋮ → "Unarchive"

### ❌ Problem: Can't find moved chat
**Solution:**
- Check folder where moved
- Also appears in Recents
- Search conversation title

### ❌ Problem: Share link not working
**Solution:**
- Check link was copied correctly
- Try pasting in new browser tab
- Ensure backend running

---

## Visual Comparison

### Before (No Menu):
```
Recents
  • Chat 1   [✎ Rename] [✕ Delete]
  • Chat 2   [✎ Rename] [✕ Delete]
  • Chat 3   [✎ Rename] [✕ Delete]

Limited options
```

### After (Context Menu):
```
Recents
  • Chat 1        ⋮ ← Click!
  • Chat 2        ⋮
  • Chat 3        ⋮

6 options per chat:
✓ Share
✓ Rename
✓ Move to project
✓ Pin chat
✓ Archive
✓ Delete
```

---

## Ready to Try!

1. **Restart frontend**: `npm run dev`
2. **Open app**: `http://localhost:5173`
3. **Create a few chats**
4. **Hover over any chat**
5. **Click ⋮ menu**
6. **Try all 6 options!**

Enjoy your ChatGPT-style context menu! 🎉
