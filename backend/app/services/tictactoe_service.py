"""Tic Tac Toe AI Agent service with LLM integration."""

import logging
from typing import Optional, Tuple, List

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
        # Minimax implementation requires no external model dependency.
        pass
    
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

        # Use optimal minimax play so AI is not beatable.
        move = self._get_optimal_move(game)
        if move == -1:
            return -1, "No moves available"
        return move, "optimal_minimax"
    
    def _get_fallback_move(self, game: TicTacToeGame) -> int:
        """
        Backward-compatible method name used by existing callers.

        Returns an optimal minimax move.
        """
        return self._get_optimal_move(game)

    def _get_optimal_move(self, game: TicTacToeGame) -> int:
        """Choose the best possible move using minimax."""
        available = game.get_available_moves()
        if not available:
            return -1

        best_score = float("-inf")
        best_move = available[0]

        for move in available:
            game.board[move - 1] = game.ai_symbol
            score = self._minimax(game, is_ai_turn=False)
            game.board[move - 1] = " "

            if score > best_score:
                best_score = score
                best_move = move

        logger.info(f"Optimal move selected: {best_move} (score={best_score})")
        return best_move

    def _minimax(self, game: TicTacToeGame, is_ai_turn: bool) -> int:
        """Evaluate board state recursively from the AI perspective."""
        winner = game.check_winner()
        if winner == game.ai_symbol:
            return 1
        if winner == game.human_symbol:
            return -1
        if game.is_board_full():
            return 0

        available = game.get_available_moves()

        if is_ai_turn:
            best_score = float("-inf")
            for move in available:
                game.board[move - 1] = game.ai_symbol
                score = self._minimax(game, is_ai_turn=False)
                game.board[move - 1] = " "
                best_score = max(best_score, score)
            return int(best_score)

        best_score = float("inf")
        for move in available:
            game.board[move - 1] = game.human_symbol
            score = self._minimax(game, is_ai_turn=True)
            game.board[move - 1] = " "
            best_score = min(best_score, score)
        return int(best_score)
