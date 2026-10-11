import type { Product } from '../api/client'

const TINTS: Record<string, string> = {
  black: '#E7EAF3',
  white: '#EEE8DF',
  red: '#F1E6E6',
  blue: '#E3EAF5',
  green: '#E3EEE8',
  grey: '#ECEAE4',
}

const FOOTWEAR = ['shoe', 'sneaker', 'sandal', 'boot']

/** Placeholder product art until real photos exist: a silhouette on a tinted tile. */
export function ProductArt({ product, className = '' }: { product: Product; className?: string }) {
  const color = String(product.attributes.color ?? 'black')
  const isFootwear = FOOTWEAR.some((word) => product.category.slug.includes(word))

  return (
    <div
      className={`grid place-items-center overflow-hidden rounded-lg text-[#1d1f24] ${className}`}
      style={{ background: TINTS[color] ?? TINTS.black }}
      aria-hidden="true"
    >
      {isFootwear ? (
        <svg viewBox="0 0 120 60" className="w-3/5">
          <path d="M8 44c0-9 4-20 12-24 6-3 12 1 18 6 8 7 18 11 30 12 14 1 30 4 38 10 4 3 4 8 0 9H14c-4 0-6-6-6-13z" fill="currentColor" opacity=".9" />
          <path d="M8 50h100c3 0 4 3 2 5H12c-3 0-4-2-4-5z" fill="currentColor" opacity=".55" />
          <path d="M36 27l6 8M44 31l6 8M52 34l5 7" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" opacity=".8" />
        </svg>
      ) : (
        <svg viewBox="0 0 120 100" className="w-2/5">
          <path d="M38 8l-28 16 10 20 12-6v54h56V38l12 6 10-20L82 8c-4 8-12 12-22 12S42 16 38 8z" fill="currentColor" opacity=".9" />
        </svg>
      )}
    </div>
  )
}
