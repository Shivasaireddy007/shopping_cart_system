export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`font-display text-xl font-extrabold tracking-tight text-brand ${className}`}>
      Shopping <span className="text-accent">Cart</span>
    </span>
  )
}
