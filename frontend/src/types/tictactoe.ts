/**
 * Tic Tac Toe types and interfaces
 */

export interface GameState {
  game_id: string;
  board: (string | null)[];
  status: "active" | "win" | "lose" | "draw";
  message: string;
  game_over: boolean;
  winner: "X" | "O" | null;
  available_moves: number[];
  move_history: Array<[number, string]>;
}

export interface MoveResponse {
  success: boolean;
  human_move: number | null;
  ai_move: number | null;
  board: (string | null)[];
  status: "active" | "win" | "lose" | "draw";
  message: string;
  game_over: boolean;
  winner: "X" | "O" | null;
}

export interface NewGameResponse {
  game_id: string;
  board: (string | null)[];
  message: string;
  available_moves: number[];
}

export type BoardCell = "X" | "O" | " " | null;
