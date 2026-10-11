import { discountPercent, formatPaise } from '../lib/money'

export function Price({ price, mrp, size = 'md' }: { price: number; mrp?: number | null; size?: 'md' | 'lg' }) {
  const off = discountPercent(price, mrp)
  return (
    <div className="flex flex-wrap items-baseline gap-2 tabular">
      <span className={`font-bold ${size === 'lg' ? 'text-2xl' : ''}`}>{formatPaise(price)}</span>
      {off !== null && mrp ? (
        <>
          <span className="text-sm text-muted line-through">{formatPaise(mrp)}</span>
          <span className="text-sm font-semibold text-good">{off}% off</span>
        </>
      ) : null}
    </div>
  )
}
