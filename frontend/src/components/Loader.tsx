import { motion } from "framer-motion"

export function Loader({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-white/60">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent-soft)]"
            animate={{ y: [0, -5, 0] }}
            transition={{
              duration: 0.7,
              repeat: Infinity,
              delay: i * 0.12,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}
