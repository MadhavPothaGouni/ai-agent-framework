import { AnimatePresence, motion } from "framer-motion"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { Loader } from "../components/Loader"
import { apiErrorMessage, sendChat } from "../lib/api"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return

    setError(null)
    setInput("")
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }])
    setSending(true)

    try {
      const res = await sendChat(text, sessionId)
      setSessionId(res.session_id)
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: res.reply },
      ])
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to send message."))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-6 py-8">
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-white">Chat</h1>
        <p className="text-sm text-white/40">
          Talking to the Planner agent{sessionId ? " — memory active for this session" : ""}.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {messages.length === 0 && !sending && (
          <div className="flex h-full items-center justify-center text-sm text-white/30">
            Say something to get started.
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`mb-3 flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-soft)] text-white"
                    : "border border-[var(--color-border)] bg-[var(--color-surface)] text-white/85"
                }`}
              >
                {m.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {sending && (
          <div className="mb-3 flex justify-start">
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
              <Loader />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <p className="mb-2 text-sm text-[var(--color-danger)]">{error}</p>}

      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the agent…"
          className="flex-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-[var(--color-accent)]"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-xl bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-soft)] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-[var(--color-accent)]/25 transition-transform active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
