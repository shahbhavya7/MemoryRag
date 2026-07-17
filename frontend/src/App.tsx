import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import Background from "./components/Background";
import ProtectedRoute from "./components/ProtectedRoute";
import ChatPage from "./pages/ChatPage";
import EvaluationPage from "./pages/EvaluationPage";
import LoginPage from "./pages/LoginPage";
import MemoriesPage from "./pages/MemoriesPage";
import RegisterPage from "./pages/RegisterPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <>
      {/* Ambient animated backdrop that all the glass panels blur. */}
      <Background />

      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Everything below requires a token in memory */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/memories" element={<MemoriesPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
          </Route>
        </Route>

        {/* Default + unknown routes land on chat (which redirects to login if needed) */}
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </>
  );
}
