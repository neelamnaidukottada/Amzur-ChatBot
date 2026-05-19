import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

const ChatPage = lazy(() => import('./components/ChatPage').then((m) => ({ default: m.ChatPage })));
const LoginPage = lazy(() => import('./components/LoginPage').then((m) => ({ default: m.LoginPage })));
const Project10Page = lazy(() => import('./components/Project10Page').then((m) => ({ default: m.Project10Page })));
const TicTacToePage = lazy(() => import('./components/TicTacToePage').then((m) => ({ default: m.TicTacToePage })));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('auth_token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense
        fallback={
          <div className="min-h-screen flex items-center justify-center text-gray-600 text-sm">
            Loading...
          </div>
        }
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/research-digest-agent"
            element={
              <ProtectedRoute>
                <Project10Page />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tictactoe"
            element={
              <ProtectedRoute>
                <TicTacToePage />
              </ProtectedRoute>
            }
          />
          <Route path="/project-10" element={<Navigate to="/research-digest-agent" replace />} />
          <Route path="/project-11" element={<Navigate to="/tictactoe" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
