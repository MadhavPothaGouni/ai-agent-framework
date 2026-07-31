import { Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AuthProvider, useAuth } from "./context/AuthContext"
import { ChatPage } from "./pages/ChatPage"
import { LoginPage } from "./pages/LoginPage"
import { RunHistoryPage } from "./pages/RunHistoryPage"
import { SignupPage } from "./pages/SignupPage"
import { WorkflowPage } from "./pages/WorkflowPage"

function RootRedirect() {
  const { isAuthenticated } = useAuth()
  return <Navigate to={isAuthenticated ? "/chat" : "/login"} replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <Layout>
              <ChatPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/workflow"
        element={
          <ProtectedRoute>
            <Layout>
              <WorkflowPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/runs"
        element={
          <ProtectedRoute>
            <Layout>
              <RunHistoryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
