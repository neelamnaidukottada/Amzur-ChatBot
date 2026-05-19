"""Tic Tac Toe AI Agent service with LLM integration."""

import logging
from typing import Optional, Tuple, List
from langchain_core.messages import HumanMessage, SystemMessage
from app.ai.llm import get_chat_llm
import re

logger = logging.getLogger(__name__)


class TicTacToeGame:
    """Manages Tic Tac Toe game state and logic."""
    
    # Board positions:
    # 1 | 2 | 3
    # 4 | 5 | 6
    # 7 | 8 | 9
    
    def __init__(self):
        """Initialize a new game."""
        self.board: List[str] = [" "] * 9  # Index 0-8 represents positions 1-9
        self.human_symbol = "X"
        self.ai_symbol = "O"
        self.game_over = False
        self.winner = None
        self.move_history = []
    
    def get_board_display(self) -> str:
        """Return formatted board representation."""
        return f"""
{self.board[0]} | {self.board[1]} | {self.board[2]}
---------
{self.board[3]} | {self.board[4]} | {self.board[5]}
---------
{self.board[6]} | {self.board[7]} | {self.board[8]}
"""
    
    def get_board_state(self) -> str:
        """Return compact board state for LLM."""
        positions = []
        for i in range(9):
            if self.board[i] != " ":
                positions.append(f"{i+1}={self.board[i]}")
        return ",".join(positions) if positions else "empty"
    
    def is_valid_move(self, position: int) -> Tuple[bool, str]:
        """
        Validate if move is legal.
        
        Args:
            position: Move position (1-9)
        
        Returns:
            (is_valid, error_message)
        """
        if not isinstance(position, int):
            return False, "Move must be an integer"
        
        if position < 1 or position > 9:
            return False, f"Move must be 1-9, got {position}"
        
        if self.board[position - 1] != " ":
            return False, f"Cell {position} is already occupied"
        
        return True, ""
    
    def make_move(self, position: int, symbol: str) -> Tuple[bool, str]:
        """
        Make a move on the board.
        
        Args:
            position: Move position (1-9)
            symbol: "X" for human, "O" for AI
        
        Returns:
            (success, message)
        """
        is_valid, error = self.is_valid_move(position)
        if not is_valid:
            return False, error
        
        self.board[position - 1] = symbol
        self.move_history.append((position, symbol))
        return True, ""
    
    def get_available_moves(self) -> List[int]:
        """Return list of available moves (1-9)."""
        return [i + 1 for i, cell in enumerate(self.board) if cell == " "]
    
    def check_winner(self) -> Optional[str]:
        """Check if there's a winner. Returns 'X', 'O', or None."""
        # Winning combinations (0-indexed)
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6],              # Diagonals
        ]
        
        for combo in winning_combos:
            if (self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != " "):
                return self.board[combo[0]]
        
        return None
    
    def is_board_full(self) -> bool:
        """Check if board is full (draw)."""
        return all(cell != " " for cell in self.board)
    
    def get_game_status(self) -> dict:
        """Get current game status."""
        winner = self.check_winner()
        is_full = self.is_board_full()
        
        if winner:
            status = "win" if winner == self.ai_symbol else "lose"
            self.game_over = True
            self.winner = winner
            return {
                "status": status,
                "message": f"{winner} wins!",
                "board": self.board,
                "game_over": True
            }
        
        if is_full:
            self.game_over = True
            return {
                "status": "draw",
                "message": "It's a draw!",
                "board": self.board,
                "game_over": True
            }
        
        return {
            "status": "active",
            "message": "Game in progress",
            "board": self.board,
            "game_over": False
        }


class TicTacToeAIAgent:
    """AI Agent for Tic Tac Toe using LLM."""
    
    def __init__(self):
        """Initialize AI Agent."""
        self.llm = get_chat_llm()
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for Tic Tac Toe AI."""
        return """You are an expert Tic Tac Toe player with the following objectives:

1. Win if possible - identify and play winning moves
2. Block opponent if they are about to win
3. Prioritize strategic positions: center (5) > corners (1,3,7,9) > sides (2,4,6,8)
4. Never choose an occupied cell
5. Return ONLY one number from 1-9 representing your move

Board positions:
1 | 2 | 3
4 | 5 | 6
7 | 8 | 9

Rules:
- AI symbol = O
- Human symbol = X
- If winning move exists → play it
- If opponent can win next turn → block it
- Otherwise choose the best strategic move

CRITICAL: Output ONLY a single number (1-9) with no explanation, no reasoning, no extra text.
Example response format: 5
"""
    
    def get_ai_move(self, game: TicTacToeGame, max_retries: int = 3) -> Tuple[int, str]:
        """
        Get AI move using LLM with validation.
        
        Args:
            game: Current game state
            max_retries: Number of retries for invalid moves
        
        Returns:
            (move, error_or_status)
        """
        available_moves = game.get_available_moves()
        
        if not available_moves:
            return -1, "No moves available"
        
        # Try to get valid move from LLM
        for attempt in range(max_retries):
            try:
                # Build context
                board_display = game.get_board_display()
                user_message = f"""Current board state:
{board_display}

Available positions: {available_moves}

Your move (1-9):"""
                
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_message)
                ]
                
                # Get LLM response
                response = self.llm.invoke(messages)
                move_str = response.content.strip()
                
                logger.info(f"LLM raw response: '{move_str}'")
                
                # Extract number from response (handle cases where LLM adds extra text)
                move = self._extract_move(move_str)
                
                if move is None:
                    logger.warning(f"Attempt {attempt + 1}: Could not parse move from: '{move_str}'")
                    continue
                
                # Validate move
                is_valid, error = game.is_valid_move(move)
                
                if not is_valid:
                    logger.warning(f"Attempt {attempt + 1}: Invalid move {move} - {error}")
                    # Fallback: pick best strategic move
                    if attempt == max_retries - 1:
                        move = self._get_fallback_move(game)
                        logger.info(f"Using fallback move: {move}")
                        return move, "Fallback strategic move"
                    continue
                
                logger.info(f"Valid AI move: {move}")
                return move, "success"
            
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Error getting AI move: {e}")
                if attempt == max_retries - 1:
                    move = self._get_fallback_move(game)
                    logger.info(f"Using fallback move due to error: {move}")
                    return move, f"Error: {str(e)}, using fallback"
        
        # Final fallback
        move = self._get_fallback_move(game)
        logger.warning(f"All LLM attempts failed, using fallback: {move}")
        return move, "All LLM attempts failed, using fallback"
    
    def _extract_move(self, response: str) -> Optional[int]:
        """
        Extract move number from LLM response.
        
        Handles cases where LLM adds extra text.
        """
        # Remove whitespace
        response = response.strip()
        
        # Try to find first number 1-9
        matches = re.findall(r'\b([1-9])\b', response)
        
        if matches:
            try:
                move = int(matches[0])
                if 1 <= move <= 9:
                    return move
            except ValueError:
                pass
        
        # Try direct integer parse
        try:
            move = int(response)
            if 1 <= move <= 9:
                return move
        except ValueError:
            pass
        
        return None
    
    def _get_fallback_move(self, game: TicTacToeGame) -> int:
        """
        Get strategic fallback move when LLM fails.
        
        Priority: center > corners > sides
        """
        board = game.board
        available = game.get_available_moves()
        
        if not available:
            return -1
        
        # Priority order: center, corners, sides
        priority = [5, 1, 3, 7, 9, 2, 4, 6, 8]
        
        for position in priority:
            if position in available:
                logger.info(f"Fallback: Choosing strategic position {position}")
                return position
        
        # Should never reach here
        return available[0]
