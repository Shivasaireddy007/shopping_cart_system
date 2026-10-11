const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

/** 899900 paise -> "₹8,999". Uses Indian digit grouping (₹1,09,999). */
export function formatPaise(paise: number): string {
  return inr.format(Math.round(paise / 100))
}

/** Percentage off MRP, rounded down, or null when there is no discount. */
export function discountPercent(price: number, mrp: number | null | undefined): number | null {
  if (!mrp || mrp <= price) return null
  return Math.floor(((mrp - price) / mrp) * 100)
}
