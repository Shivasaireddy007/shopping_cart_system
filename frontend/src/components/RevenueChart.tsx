import { useState } from 'react'

import { formatPaise } from '../lib/money'

type Day = { date: string; revenue: number; orders: number }

const W = 560
const H = 220
const PAD = { top: 16, right: 12, bottom: 28, left: 52 }
const BAR = 24
const RADIUS = 4

const dayLabel = new Intl.DateTimeFormat('en-IN', { weekday: 'short' })
const longDate = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'short' })

/** Rounds up to 1, 2 or 5 × a power of ten so the axis has clean ticks. */
function niceMax(value: number): number {
  if (value <= 0) return 100000
  const power = 10 ** Math.floor(Math.log10(value))
  return ([1, 2, 5, 10].find((step) => step * power >= value) ?? 10) * power
}

/** ₹ axis labels in Indian units: ₹50k, ₹1.5L. */
function shortRupees(paise: number): string {
  const rupees = paise / 100
  if (rupees >= 100000) return `₹${+(rupees / 100000).toFixed(1)}L`
  if (rupees >= 1000) return `₹${+(rupees / 1000).toFixed(1)}k`
  return `₹${rupees}`
}

/** A bar rounded only at its data end, square on the baseline. */
function barPath(x: number, y: number, width: number, height: number): string {
  const r = Math.min(RADIUS, height, width / 2)
  const base = y + height
  return `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${base} Z`
}

export function RevenueChart({ days }: { days: Day[] }) {
  const [active, setActive] = useState<number | null>(null)
  const max = niceMax(Math.max(...days.map((d) => d.revenue)))
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const slot = plotW / days.length
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH
  const ticks = [0, max / 2, max]
  const shown = active === null ? null : days[active]

  return (
    <figure className="relative grid gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Revenue for the last 7 days, up to ${shortRupees(Math.max(...days.map((d) => d.revenue)))} a day`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--color-line)" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--color-muted)">{shortRupees(t)}</text>
          </g>
        ))}
        {days.map((d, i) => {
          const x = PAD.left + slot * i + (slot - BAR) / 2
          const h = Math.max(0, PAD.top + plotH - y(d.revenue))
          const label = `${longDate.format(new Date(d.date))}: ${formatPaise(d.revenue)} from ${d.orders} order${d.orders === 1 ? '' : 's'}`
          return (
            <g
              key={d.date}
              tabIndex={0}
              role="button"
              aria-label={label}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(i)}
              onBlur={() => setActive(null)}
              className="cursor-default outline-none"
            >
              {/* Hit target: the whole slot, taller and wider than the bar. */}
              <rect x={PAD.left + slot * i} y={PAD.top} width={slot} height={plotH} fill="transparent" />
              {h > 0 ? (
                <path d={barPath(x, y(d.revenue), BAR, h)} fill="var(--color-accent)" opacity={active === null || active === i ? 1 : 0.45} />
              ) : null}
              <text x={x + BAR / 2} y={H - 8} textAnchor="middle" fontSize={11} fill={active === i ? 'var(--color-ink)' : 'var(--color-muted)'} fontWeight={active === i ? 600 : 400}>
                {i === days.length - 1 ? 'Today' : dayLabel.format(new Date(d.date))}
              </text>
            </g>
          )
        })}
      </svg>
      {shown ? (
        <div className="pointer-events-none absolute top-0 right-0 rounded-lg border border-line bg-surface px-3 py-2 text-sm shadow-sm" role="status">
          <p className="font-semibold">{longDate.format(new Date(shown.date))}</p>
          <p className="tabular">{formatPaise(shown.revenue)} · {shown.orders} order{shown.orders === 1 ? '' : 's'}</p>
        </div>
      ) : null}
      <table className="sr-only">
        <caption>Revenue by day</caption>
        <thead><tr><th>Day</th><th>Revenue</th><th>Orders</th></tr></thead>
        <tbody>
          {days.map((d) => <tr key={d.date}><td>{d.date}</td><td>{formatPaise(d.revenue)}</td><td>{d.orders}</td></tr>)}
        </tbody>
      </table>
    </figure>
  )
}
