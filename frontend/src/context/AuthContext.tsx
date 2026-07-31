import { createContext, useContext, useMemo, useState, type ReactNode } from "react"
import { clearToken, getToken, setToken as persistToken } from "../lib/api"

interface AuthContextValue {
  token: string | null
  isAuthenticated: boolean
  setAuthToken: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken())

  const setAuthToken = (newToken: string) => {
    persistToken(newToken)
    setTokenState(newToken)
  }

  const logout = () => {
    clearToken()
    setTokenState(null)
  }

  const value = useMemo<AuthContextValue>(
    () => ({ token, isAuthenticated: Boolean(token), setAuthToken, logout }),
    [token],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return ctx
}
