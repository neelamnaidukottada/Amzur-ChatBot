# Project 11 — Tic Tac Toe AI Agent | QUICK START

## 🚀 Get Running in 2 Minutes

### 1. Start Backend
```bash
cd backend
python -m venv venv  # if needed
venv\Scripts\Activate.ps1  # or activate
pip install -r requirements.txt  # if needed
uvicorn app.main:app --reload
```
✅ Backend runs at: `http://localhost:8000`

### 2. Start Frontend
```bash
# New terminal
cd frontend
npm install  # if needed
npm run dev
```
✅ Frontend runs at: `http://localhost:5173`

### 3. Play the Game
```
Visit: http://localhost:5173/tictactoe
```

## 🎮 How to Play

1. **Click "New Game"** to start
2. **Click any position** (1-9) on the board
3. **AI responds** automatically
4. **Keep playing** until someone wins or it's a draw
5. **Click "Reset"** to play again

## 📊 Board Layout

```
1 | 2 | 3
---------
4 | 5 | 6
---------
7 | 8 | 9
```

## 🤖 AI Strategy

The AI will:
- ✅ **Win** if it can
- ✅ **Block** your winning moves
- ✅ **Prioritize**: Center → Corners → Sides
- ✅ **Never** make invalid moves
- ✅ **Fallback** gracefully if LLM fails

## 📋 What's Implemented

### ✅ Backend (`backend/`)
- `app/services/tictactoe_service.py` - Game logic + AI agent
- `app/api/tictactoe.py` - REST API endpoints
- LLM integration with LiteLLM

### ✅ Frontend (`frontend/`)
- `src/components/TicTacToePage.tsx` - Game UI
- `src/types/tictactoe.ts` - TypeScript types
- `src/lib/api.ts` - API client methods
- Routes: `/tictactoe` and `/project-11`

### ✅ Documentation
- `PROJECT_11_TICTACTOE_GUIDE.md` - Complete technical guide
- `PROJECT_11_IMPLEMENTATION_CHECKLIST.md` - Feature checklist

## 🔧 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/games/tictactoe/new` | Create game |
| GET | `/api/games/tictactoe/{id}/state` | Get state |
| POST | `/api/games/tictactoe/{id}/move` | Make move |
| POST | `/api/games/tictactoe/{id}/reset` | Reset |
| DELETE | `/api/games/tictactoe/{id}` | Delete |

## 🛡️ Validation

**Every move is validated:**
1. ✅ Is it 1-9? (Pydantic + Backend)
2. ✅ Is the cell empty? (Backend)
3. ✅ Is AI move valid? (AI Agent + Backend)

**If LLM fails:**
- ↻ Retry up to 3 times
- → Use strategic fallback move

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Need 3.8+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check LiteLLM keys in .env
LITELLM_API_KEY=your_key
LITELLM_PROXY_URL=https://litellm.amzur.com
```

### Frontend won't load
```bash
# Check Node version
node --version  # Need 16+

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check API URL
# It should connect to: http://localhost:8000
```

### AI not responding
- Check: Backend logs (see LLM response)
- Check: LiteLLM API key in `.env`
- Check: Network to litellm.amzur.com

### Invalid move error
- Possible causes:
  - Cell already occupied
  - Position not 1-9
  - Check: Backend logs for details

## 📂 Key Files

```
backend/
  app/
    services/
      tictactoe_service.py     ← Game logic + AI
    api/
      tictactoe.py             ← Endpoints
    main.py                     ← Router registration

frontend/
  src/
    components/
      TicTacToePage.tsx        ← Game UI
    types/
      tictactoe.ts             ← TypeScript types
    lib/
      api.ts                   ← API methods
    App.tsx                     ← Routes
```

## 🎯 What You Can Learn

1. **LLM Integration** - Using language models for decisions
2. **Validation Layers** - Multi-level input validation
3. **Fallback Strategies** - Graceful error handling
4. **System Prompts** - Crafting effective prompts
5. **Output Parsing** - Extracting data from LLM
6. **Full Stack Development** - Frontend to Backend
7. **Game Logic** - Implementing game rules
8. **React Hooks** - `useState`, `useEffect`

## 💡 Next Steps

### Want to Extend It?

**Easy**: 
- Add move history display
- Show captured pieces
- Add sound effects

**Medium**:
- Difficulty levels (Random/Smart/Minimax)
- Game statistics
- Replay feature

**Hard**:
- 4x4 or 5x5 board
- Multiplayer mode
- AI fine-tuning

## 📞 Quick Reference

**Start Game**: `POST /api/games/tictactoe/new`
**Make Move**: `POST /api/games/tictactoe/{game_id}/move` with `position: 1-9`
**Game Statuses**: `"active"`, `"win"`, `"lose"`, `"draw"`
**Symbols**: `"X"` = Human, `"O"` = AI

## ✨ You're All Set!

Go to `http://localhost:5173/tictactoe` and start playing! 🎮

The AI will make intelligent moves using LLM, with full validation and fallback support.

Good luck beating the AI! 🤖 vs 👤

---

**Need Help?**
- Check logs: `backend/` terminal shows LLM calls
- Check network: Frontend network tab shows API calls
- Read full guide: `PROJECT_11_TICTACTOE_GUIDE.md`
