# Project 11 — Tic Tac Toe AI Agent

## Overview

An intelligent Tic Tac Toe game powered by LLM (LiteLLM). The AI agent uses your Lite LLM integration to make strategic decisions while the backend enforces strict validation to prevent hallucinations or invalid moves.

## Architecture

```
Frontend (React)
    ↓
API Client (TypeScript)
    ↓
FastAPI Backend
    ├─ Validation Layer (checks 1-9 and empty cells)
    ├─ Game Logic (TicTacToeGame)
    └─ AI Agent (LLM + Fallback Strategy)
```

### Key Design Principles ✅

| Principle | Implementation |
|-----------|-----------------|
| **LLM = Decision Engine Only** | LLM only determines move strategy |
| **Backend = Rule Enforcement** | Backend validates ALL moves |
| **Frontend = UI Only** | Frontend displays state, doesn't process logic |
| **Strict Validation** | Move must be 1-9 AND cell must be empty |
| **Fallback Mechanism** | If LLM fails, use strategic fallback |
| **No Hallucination** | LLM output parsed carefully + validated |

## Files Created

### Backend

#### 1. **Service: `backend/app/services/tictactoe_service.py`**

**TicTacToeGame Class**
- Manages board state (9 cells, indexed 0-8 representing positions 1-9)
- Methods:
  - `make_move(position, symbol)` - validates AND applies move
  - `is_valid_move(position)` - checks if 1-9 and cell is empty
  - `check_winner()` - checks all winning combinations
  - `get_available_moves()` - returns list of playable positions
  - `get_game_status()` - returns current state (active/win/lose/draw)

**TicTacToeAIAgent Class**
- Integrates with LiteLLM for strategic decision-making
- Methods:
  - `get_ai_move(game)` - gets validated move from LLM with retries
  - `_extract_move(response)` - carefully parses LLM output (regex + fallback)
  - `_get_fallback_move(game)` - uses strategic priority when LLM fails

**AI Strategy (System Prompt)**
1. Win if possible
2. Block opponent if they can win
3. Prioritize: Center (5) > Corners (1,3,7,9) > Sides (2,4,6,8)
4. Never choose occupied cells
5. Output ONLY a single number

#### 2. **API Router: `backend/app/api/tictactoe.py`**

Endpoints (all behind auth, Pydantic validation):

- **POST `/api/games/tictactoe/new`**
  - Creates new game
  - Returns: `game_id`, board, message

- **GET `/api/games/tictactoe/{game_id}/state`**
  - Gets current game state
  - Returns: board, status, available_moves, history

- **POST `/api/games/tictactoe/{game_id}/move`**
  - Makes human move + gets AI response
  - Input: `position` (1-9, validated by Pydantic)
  - Backend validation:
    1. Move is 1-9? ✓
    2. Cell is empty? ✓
    3. AI move is valid? ✓
  - Returns: human_move, ai_move, board, status, game_over

- **POST `/api/games/tictactoe/{game_id}/reset`**
  - Resets game to initial state

- **DELETE `/api/games/tictactoe/{game_id}`**
  - Deletes game session

- **GET `/api/games/tictactoe/health`**
  - Service health check

#### 3. **Main App Update: `backend/app/main.py`**
- Registered tictactoe router
- Router available at `/api/games/tictactoe/*`

### Frontend

#### 1. **Types: `frontend/src/types/tictactoe.ts`**

```typescript
GameState          // Full game state from backend
MoveResponse       // Response after making a move
NewGameResponse    // Response from creating new game
BoardCell          // Type for each cell
```

#### 2. **API Client: `frontend/src/lib/api.ts`**

Added methods to existing `ApiClient`:
- `createTicTacToeGame()` - POST /new
- `getTicTacToeGameState(gameId)` - GET state
- `makeMove(gameId, position)` - POST move with validation
- `resetTicTacToeGame(gameId)` - POST reset
- `deleteTicTacToeGame(gameId)` - DELETE game

#### 3. **Component: `frontend/src/components/TicTacToePage.tsx`**

Interactive React component featuring:
- 3x3 board grid with emoji display (❌ for X, ⭕ for O)
- Position reference guide (1-9)
- Status display (game state, messages)
- New Game / Reset buttons
- AI strategy info panel
- Loading states and error handling
- Responsive Tailwind design

#### 4. **Routes: `frontend/src/App.tsx`**

Added routes:
- `/tictactoe` - Main game page (protected)
- `/project-11` - Alias to `/tictactoe`

## Move Validation Flow

```
Frontend Button Click (position)
    ↓
apiClient.makeMove(gameId, position)
    ↓
Backend: MoveRequest
    ├─ Pydantic validates: 1 ≤ position ≤ 9 ✓
    ├─ Game.is_valid_move(position)
    │   └─ Check: board[position-1] == " " ✓
    ├─ Game.make_move(position, "X")
    ├─ Check: Human won? → Game Over
    ├─ AI.get_ai_move(game) → tries up to 3 times
    │   ├─ LLM responds
    │   ├─ Extract number (regex parsing)
    │   ├─ Validate move
    │   └─ If all fails → Strategic Fallback
    ├─ Game.make_move(ai_move, "O")
    ├─ Check: AI won? → Game Over
    ├─ Check: Draw? → Game Over
    └─ Return: MoveResponse with board, status, winner
    ↓
Frontend: Update board + display status
```

## AI Agent - Detailed Logic

### System Prompt
The AI receives explicit instructions:
- Objectives ranked by priority
- Board position reference
- Symbol definitions (AI=O, Human=X)
- Rules for decisions
- **CRITICAL**: Output ONLY a number

### Extraction & Validation

1. **LLM Response Parsing** (`_extract_move`)
   ```python
   # Try regex first (finds first digit 1-9)
   # Then try direct int parse
   # Handle various LLM response formats
   ```

2. **Move Validation** (`is_valid_move`)
   ```python
   1. Is it an integer?
   2. Is it 1-9?
   3. Is the cell empty?
   ```

3. **Retry Logic** (max 3 attempts)
   - If parsing fails → retry
   - If validation fails → retry
   - If all fail → use fallback

### Fallback Strategy (`_get_fallback_move`)
Priority order when LLM fails:
1. **Center**: Position 5
2. **Corners**: Positions 1, 3, 7, 9
3. **Sides**: Positions 2, 4, 6, 8

## Usage Examples

### Starting a Game

```bash
# Frontend: User clicks "New Game"
POST /api/games/tictactoe/new
Response: {
  "game_id": "abc123",
  "board": [" ", " ", " ", " ", " ", " ", " ", " ", " "],
  "message": "Game started. You are X...",
  "available_moves": [1, 2, 3, 4, 5, 6, 7, 8, 9]
}
```

### Making a Move

```bash
POST /api/games/tictactoe/abc123/move
Body: {
  "game_id": "abc123",
  "position": 5  # Center position
}

Response: {
  "success": true,
  "human_move": 5,
  "ai_move": 1,
  "board": ["O", " ", " ", " ", "X", " ", " ", " ", " "],
  "status": "active",
  "message": "Game in progress",
  "game_over": false,
  "winner": null
}
```

### Game Over - Human Wins

```bash
POST /api/games/tictactoe/abc123/move
Body: { "game_id": "abc123", "position": 3 }

Response: {
  "success": true,
  "human_move": 3,
  "ai_move": null,
  "board": ["O", " ", "X", " ", "X", " ", " ", " ", "X"],
  "status": "win",
  "message": "X wins!",
  "game_over": true,
  "winner": "X"
}
```

## Configuration

### Environment Variables
Located in `.env`:
```
LITELLM_PROXY_URL=https://litellm.amzur.com
LITELLM_API_KEY=your_key
LLM_MODEL=gpt-4-mini  # or your model
```

### Temperature Settings
- LLM temperature: 0.7 (balanced creativity + consistency)
- Can adjust in `get_chat_llm()` if needed

## Testing the Implementation

### 1. **Backend Test**
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Test in browser or curl
curl -X POST http://localhost:8000/api/games/tictactoe/new
```

### 2. **Frontend Test**
```bash
# Start frontend
cd frontend
npm run dev

# Visit: http://localhost:5173/tictactoe
```

### 3. **Full Game Flow**
1. Click "New Game" to start
2. Click position (1-9) to make your move
3. AI automatically responds
4. Game ends when someone wins or board is full
5. Click "Reset" to play again

## Monitoring & Logging

### Backend Logs
Check logs for:
- ✅ Game creation/deletion
- ✅ Move validation results
- ✅ LLM responses (raw output)
- ✅ AI move selection (with reasoning)
- ⚠️ Failed moves (with error details)
- ⚠️ LLM retries
- ⚠️ Fallback strategy triggered

### Example Log Output
```
INFO: Game abc123: Human moved to 5
INFO: LLM raw response: '1'
INFO: Valid AI move: 1
INFO: Game abc123: AI moved to 1 (success)
```

## Troubleshooting

### LLM Not Responding
- Check: `LITELLM_API_KEY` and `LITELLM_PROXY_URL`
- Check: Network connectivity to litellm.amzur.com
- Check: Model name in settings

### Invalid Move Despite Validation
- Backend checks position (1-9) via Pydantic
- Backend checks cell is empty before move
- Should never reach frontend with invalid move
- If occurs: check logs for validation bypass

### AI Making Same Move Twice
- Impossible: `board[position-1]` checked before move
- Check: Board state sync between frontend/backend

### AI Not Playing Strategically
- Check: System prompt in `_build_system_prompt()`
- Check: LLM temperature and model
- Monitor: LLM raw responses in logs

## Future Enhancements

1. **Difficulty Levels**
   - Easy: Random moves only
   - Medium: Current strategic AI
   - Hard: Minimax algorithm

2. **Game Statistics**
   - Track wins/losses/draws
   - Display in database
   - Show streaks

3. **Multiplayer**
   - Two humans play together
   - Persistent multiplayer sessions

4. **Extended Board**
   - 4x4 or 5x5 variants
   - Custom board sizes

5. **AI Improvements**
   - Fine-tuned model for Tic Tac Toe
   - Few-shot prompting with game examples

## Summary

✅ **Validation**: Every move validated at backend before processing  
✅ **LLM Integration**: Uses LiteLLM for intelligent decisions  
✅ **Fallback Strategy**: Strategic moves when LLM fails  
✅ **Error Handling**: Retry logic + graceful degradation  
✅ **Frontend UI**: Interactive React component with real-time updates  
✅ **Architecture**: Clean separation: LLM = logic, Backend = rules, Frontend = display  

You're now an expert in AI-powered Tic Tac Toe agents! 🎮🤖
