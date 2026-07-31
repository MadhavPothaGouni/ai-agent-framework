import { AnimatePresence, motion } from "framer-motion"
import type { ReactNode } from "react"
import { NavLink, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"

const NAV_ITEMS = [
  { to: "/chat", label: "Chat", icon: ChatIcon },
  { to: "/workflow", label: "Workflow", icon: WorkflowIcon },
  { to: "/runs", label: "Run History", icon: HistoryIcon },
]

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { logout } = useAuth()

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[var(--color-bg)] text-white">
      <aside className="flex w-64 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-xl">
        <div className="flex items-center gap-2 px-6 py-6">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-accent-soft)] shadow-lg shadow-[var(--color-accent)]/30" />
          <span className="text-sm font-semibold tracking-wide text-white/90">
            Agent Framework
          </span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "text-white"
                    : "text-white/50 hover:bg-white/5 hover:text-white/80"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="nav-pill"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-[var(--color-accent)]/25 to-transparent"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <item.icon className="relative z-10 h-4 w-4" />
                  <span className="relative z-10">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[var(--color-border)] p-3">
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/50 transition-colors hover:bg-white/5 hover:text-[var(--color-danger)]"
          >
            <LogoutIcon className="h-4 w-4" />
            Log out
          </button>
        </div>
      </aside>

      <main className="relative flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="h-full"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}

function ChatIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.9 9.9 0 0 1-3.8-.75L3 20l1.2-3.6A7.9 7.9 0 0 1 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"
      />
    </svg>
  )
}

function WorkflowIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 6h4m0 0V4m0 2v2m4-2h8m-8 8h4m0 0v-2m0 2v2m4-2h4M4 18h8"
      />
      <circle cx="4" cy="6" r="1.6" />
      <circle cx="12" cy="14" r="1.6" />
      <circle cx="20" cy="18" r="1.6" />
    </svg>
  )
}

function HistoryIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 2" />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.5 12a8.5 8.5 0 1 0 2.7-6.2M3.5 5v4h4"
      />
    </svg>
  )
}

function LogoutIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
      />
    </svg>
  )
}
