import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';

export const TicTacToePage: React.FC = () => {
  const [gameId, setGameId] = useState<string | null>(null);
  const [board, setBoard] = useState<string[]>(Array(9).fill(' '));
  const [gameStatus, setGameStatus] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [gameOver, setGameOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<number | null>(null);
  const [hasError, setHasError] = useState(false);
  const [initLoading, setInitLoading] = useState(true);
  const [isLocalMode, setIsLocalMode] = useState(false);

  const winningLines = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],
    [0, 3, 6], [1, 4, 7], [2, 5, 8],
    [0, 4, 8], [2, 4, 6],
  ];

  const getWinner = (cells: string[]): string | null => {
    for (const [a, b, c] of winningLines) {
      if (cells[a] !== ' ' && cells[a] === cells[b] && cells[b] === cells[c]) {
        return cells[a];
      }
    }
    return null;
  };

  const minimax = (cells: string[], isAiTurn: boolean): number => {
    const winner = getWinner(cells);
    if (winner === 'O') return 1;
    if (winner === 'X') return -1;
    if (cells.every((c) => c !== ' ')) return 0;

    const available = cells
      .map((cell, index) => ({ cell, index }))
      .filter((x) => x.cell === ' ')
      .map((x) => x.index);

    if (isAiTurn) {
      let best = -Infinity;
      for (const idx of available) {
        const next = [...cells];
        next[idx] = 'O';
        best = Math.max(best, minimax(next, false));
      }
      return best;
    }

    let best = Infinity;
    for (const idx of available) {
      const next = [...cells];
      next[idx] = 'X';
      best = Math.min(best, minimax(next, true));
    }
    return best;
  };

  const getStrategicAiMove = (cells: string[]): number => {
    const available = cells
      .map((cell, index) => ({ cell, index }))
      .filter((x) => x.cell === ' ')
      .map((x) => x.index);

    if (available.length === 0) return -1;

    let bestScore = -Infinity;
    let bestMove = available[0];

    for (const idx of available) {
      const next = [...cells];
      next[idx] = 'O';
      const score = minimax(next, false);
      if (score > bestScore) {
        bestScore = score;
        bestMove = idx;
      }
    }

    return bestMove;
  };

  // Initialize game
  const startNewGame = async () => {
    try {
      setInitLoading(true);
      setHasError(false);
      setMessage('');
      const response = await apiClient.createTicTacToeGame();
      setIsLocalMode(false);
      setGameId(response.game_id);
      setBoard(response.board.map((cell) => (cell ?? ' ')));
      setMessage('New game started. Click any square to play.');
      setGameOver(false);
      setGameStatus('active');
    } catch (error) {
      console.warn('Falling back to local game mode:', error);
      setIsLocalMode(true);
      setGameId('local');
      setBoard(Array(9).fill(' '));
      setGameOver(false);
      setGameStatus('active');
      setMessage('Game backend unavailable. Playing in local mode.');
      setHasError(false);
    } finally {
      setInitLoading(false);
    }
  };

  // Make a move
  const handleCellClick = async (position: number) => {
    if (!gameId || gameOver || board[position - 1] !== ' ' || loading || hasError) {
      return;
    }

    try {
      setLoading(true);
      setSelectedPosition(position);

      if (isLocalMode) {
        const next = [...board];
        next[position - 1] = 'X';

        const humanWinner = getWinner(next);
        if (humanWinner === 'X') {
          setBoard(next);
          setGameOver(true);
          setGameStatus('win');
          setMessage('You win!');
          return;
        }

        if (next.every((c) => c !== ' ')) {
          setBoard(next);
          setGameOver(true);
          setGameStatus('draw');
          setMessage("It's a draw!");
          return;
        }

        const aiIdx = getStrategicAiMove(next);
        if (aiIdx >= 0) {
          next[aiIdx] = 'O';
        }

        const aiWinner = getWinner(next);
        setBoard(next);

        if (aiWinner === 'O') {
          setGameOver(true);
          setGameStatus('lose');
          setMessage('AI wins!');
        } else if (next.every((c) => c !== ' ')) {
          setGameOver(true);
          setGameStatus('draw');
          setMessage("It's a draw!");
        } else {
          setGameStatus('active');
          setMessage('Your turn.');
        }
        return;
      }

      const response = await apiClient.makeMove(gameId, position);

      setBoard(response.board.map((cell) => (cell ?? ' ')));
      setGameStatus(response.status);
      setMessage(response.message);
      setGameOver(response.game_over);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to make move';
      setMessage(`❌ ${errorMsg}`);
    } finally {
      setLoading(false);
      setSelectedPosition(null);
    }
  };

  // Reset game
  const handleReset = async () => {
    if (!gameId) return;

    try {
      setLoading(true);

      if (!isLocalMode) {
        await apiClient.resetTicTacToeGame(gameId);
      }

      setBoard(Array(9).fill(' '));
      setGameStatus('active');
      setMessage(isLocalMode ? 'Local game reset. Your turn.' : 'Game reset! Start playing again.');
      setGameOver(false);
      setHasError(false);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to reset game';
      setMessage(`❌ ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Start a new game on mount
    startNewGame();
  }, []);

  const getCellContent = (index: number) => {
    const value = board[index];
    if (value === 'X') return 'X';
    if (value === 'O') return 'O';
    return '';
  };

  const getCellClass = (index: number, position: number) => {
    const baseClass =
      'w-24 h-24 bg-white border-4 border-gray-800 text-5xl font-bold cursor-pointer hover:bg-blue-50 transition-all transform hover:scale-105 active:scale-95 rounded-lg';
    if (selectedPosition === position) {
      return `${baseClass} bg-blue-100`;
    }
    if (board[index] !== ' ') {
      return baseClass + ' cursor-not-allowed opacity-90';
    }
    if (gameOver) {
      return baseClass + ' cursor-not-allowed opacity-70';
    }
    return baseClass;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 p-4 sm:p-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-3">
              🎮 Tic Tac Toe
            </h1>
            <p className="text-lg text-gray-600">
              You are <span className="font-bold text-red-500 text-2xl">X</span> vs AI <span className="font-bold text-blue-500 text-2xl">O</span>
            </p>
          </div>

          {/* Loading State */}
          {initLoading && (
            <div className="p-6 text-center">
              <div className="animate-spin inline-block w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full mb-4"></div>
              <p className="text-gray-600 font-medium">Loading game...</p>
            </div>
          )}

          {!initLoading && (
            <>
              {/* Status Message */}
              {message && (
                <div
                  className={`p-4 rounded-lg mb-6 text-center font-semibold text-sm sm:text-base transition-all ${
                    gameStatus === 'win'
                      ? 'bg-green-100 text-green-800 border-2 border-green-300'
                      : gameStatus === 'lose'
                        ? 'bg-red-100 text-red-800 border-2 border-red-300'
                        : gameStatus === 'draw'
                          ? 'bg-yellow-100 text-yellow-800 border-2 border-yellow-300'
                          : hasError
                            ? 'bg-red-100 text-red-800 border-2 border-red-300'
                            : 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                  }`}
                >
                  {message}
                </div>
              )}

              {/* Board */}
              <div className="grid grid-cols-3 gap-3 mb-8 p-4 bg-gray-100 rounded-xl">
                {board.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => handleCellClick(index + 1)}
                    disabled={loading || gameOver || board[index] !== ' ' || hasError}
                    className={getCellClass(index, index + 1)}
                  >
                    {getCellContent(index)}
                  </button>
                ))}
              </div>

              {/* Game Stats */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6 text-center">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Moves played:</span> {board.filter((cell) => cell !== ' ').length}/9
                </p>
                {!gameOver && gameId && (
                  <p className="text-xs text-gray-500 mt-2">💡 Click any empty square to make your move</p>
                )}
              </div>

              {/* Buttons */}
              <div className="flex gap-3 mb-6">
                <button
                  onClick={handleReset}
                  disabled={loading || !gameId}
                  className="flex-1 bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition-all transform hover:scale-105 active:scale-95 disabled:cursor-not-allowed"
                >
                  {loading ? '⏳ Playing...' : '♻️ Reset'}
                </button>
                <button
                  onClick={startNewGame}
                  disabled={loading}
                  className="flex-1 bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition-all transform hover:scale-105 active:scale-95 disabled:cursor-not-allowed"
                >
                  {loading ? '⏳ Loading...' : '✨ New Game'}
                </button>
              </div>

              {/* Error Recovery */}
              {hasError && (
                <button
                  onClick={startNewGame}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-all mb-4"
                >
                  🔄 Try Again
                </button>
              )}

              {/* AI Strategy Info */}
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 p-4 rounded-lg border-2 border-blue-200">
                <p className="font-semibold text-blue-900 mb-3">🤖 AI Strategy:</p>
                <ul className="space-y-2 text-sm text-blue-800">
                  <li>✅ Wins if possible</li>
                  <li>🛡️ Blocks your winning moves</li>
                  <li>🎯 Prioritizes: Center → Corners → Sides</li>
                  <li>⚡ {isLocalMode ? 'Running in local fallback mode' : 'Powered by backend AI service'}</li>
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TicTacToePage;
