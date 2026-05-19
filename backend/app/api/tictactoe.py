"""Tic Tac Toe game API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from app.services.tictactoe_service import TicTacToeGame, TicTacToeAIAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games/tictactoe", tags=["tic-tac-toe"])

# In-memory game storage (in production, use database)
active_games = {}


class MoveRequest(BaseModel):
    """Request to make a move in the game."""
    game_id: str
    position: int = Field(..., ge=1, le=9, description="Position 1-9")


class MoveResponse(BaseModel):
    """Response after a move."""
    success: bool
    human_move: Optional[int] = None
    ai_move: Optional[int] = None
    board: List[str]
    status: str  # "active", "win", "lose", "draw"
    message: str
    game_over: bool
    winner: Optional[str] = None


class GameStateResponse(BaseModel):
    """Current game state."""
    game_id: str
    board: List[str]
    status: str
    message: str
    game_over: bool
    winner: Optional[str] = None
    available_moves: List[int]
    move_history: List[tuple]


@router.post("/new")
async def new_game() -> dict:
    """Create a new Tic Tac Toe game."""
    import uuid
    game_id = str(uuid.uuid4())
    
    try:
        game = TicTacToeGame()
        try:
            ai = TicTacToeAIAgent()
        except Exception as e:
            logger.warning(f"Failed to initialize AI agent: {e}")
            logger.info("Game will use strategic fallback moves only")
            ai = None  # Will use fallback strategy
        
        active_games[game_id] = {"game": game, "ai": ai}
        
        logger.info(f"Created new game: {game_id}")
        return {
            "game_id": game_id,
            "board": game.board,
            "message": "✅ New game started! Click any empty square to play. (AI using strategic mode)",
            "available_moves": game.get_available_moves(),
        }
    except Exception as e:
        logger.error(f"Error creating game: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create game: {str(e)}")


@router.get("/{game_id}/state")
async def get_game_state(game_id: str) -> GameStateResponse:
    """Get current game state."""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = active_games[game_id]["game"]
    status_info = game.get_game_status()
    
    return GameStateResponse(
        game_id=game_id,
        board=game.board,
        status=status_info["status"],
        message=status_info["message"],
        game_over=status_info["game_over"],
        winner=game.winner,
        available_moves=game.get_available_moves(),
        move_history=game.move_history,
    )


@router.post("/{game_id}/move")
async def make_move(game_id: str, request: MoveRequest) -> MoveResponse:
    """
    Make a human move and get AI response.
    
    Backend validation ensures:
    - Move is 1-9 ✓ (Pydantic validation)
    - Cell is empty ✓ (Game validation)
    - AI move is valid ✓ (AI agent validation)
    """
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = active_games[game_id]["game"]
    ai = active_games[game_id]["ai"]
    
    # Check game is still active
    if game.game_over:
        raise HTTPException(status_code=400, detail="Game is already over")
    
    # Validate and make human move (position already validated by Pydantic: 1-9)
    logger.info(f"Game {game_id}: Human attempts move {request.position}")
    
    success, error = game.make_move(request.position, game.human_symbol)
    if not success:
        logger.warning(f"Game {game_id}: Invalid move {request.position}: {error}")
        raise HTTPException(status_code=400, detail=f"Invalid move: {error}")
    
    logger.info(f"Game {game_id}: Human moved to {request.position}")
    
    # Check if human won
    game_status = game.get_game_status()
    if game_status["game_over"]:
        return MoveResponse(
            success=True,
            human_move=request.position,
            ai_move=None,
            board=game.board,
            status=game_status["status"],
            message=game_status["message"],
            game_over=True,
            winner=game.winner,
        )
    
    # Get AI move with validation and fallback
    try:
        if ai is None:
            # Use optimal fallback if AI agent is unavailable
            available_moves = game.get_available_moves()
            if not available_moves:
                raise HTTPException(status_code=400, detail="No valid moves available")

            fallback_agent = TicTacToeAIAgent()
            ai_move = fallback_agent._get_fallback_move(game)
            ai_status = "optimal_fallback"
        else:
            ai_move, ai_status = ai.get_ai_move(game)
        
        if ai_move == -1:
            raise HTTPException(status_code=400, detail="No valid moves available")
        
        # Make AI move
        success, error = game.make_move(ai_move, game.ai_symbol)
        if not success:
            logger.error(f"Game {game_id}: AI move {ai_move} invalid: {error}")
            raise HTTPException(status_code=500, detail=f"AI move validation failed: {error}")
        
        logger.info(f"Game {game_id}: AI moved to {ai_move} ({ai_status})")
        
        # Check game status after AI move
        game_status = game.get_game_status()
        
        return MoveResponse(
            success=True,
            human_move=request.position,
            ai_move=ai_move,
            board=game.board,
            status=game_status["status"],
            message=game_status["message"],
            game_over=game_status["game_over"],
            winner=game.winner,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Game {game_id}: Error getting AI move: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting AI move: {str(e)}")


@router.post("/{game_id}/reset")
async def reset_game(game_id: str) -> dict:
    """Reset the game to initial state."""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = active_games[game_id]["game"]
    game.__init__()  # Reset game
    
    logger.info(f"Game {game_id} reset")
    return {
        "message": "Game reset",
        "board": game.board,
        "available_moves": game.get_available_moves(),
    }


@router.delete("/{game_id}")
async def delete_game(game_id: str) -> dict:
    """Delete a game."""
    if game_id not in active_games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    del active_games[game_id]
    logger.info(f"Game {game_id} deleted")
    return {"message": "Game deleted"}


@router.get("/health")
async def health_check() -> dict:
    """Health check for Tic Tac Toe service."""
    return {
        "status": "healthy",
        "active_games": len(active_games)
    }
