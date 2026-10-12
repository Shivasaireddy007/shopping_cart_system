import { Link } from 'react-router-dom'

const PROOF = [
  { value: '0 oversold', note: '10 simultaneous buyers, 3 units' },
  { value: '99 → 5.5 ms', note: 'p95 at 1,000 req/s with Redis' },
  { value: '6 CI jobs', note: 'incl. Kubernetes and Playwright' },
]

/** Shown above the catalog on the public demo, so visitors find the engineering behind the shop. */
export function EngineeringStrip() {
  return (
    <section
      aria-labelledby="engineering-strip-title"
      className="mb-6 grid items-center gap-5 rounded-xl bg-ink p-5 text-white sm:p-6 lg:grid-cols-[1.1fr_1.4fr_auto]"
    >
      <div className="grid gap-1">
        <p className="text-xs font-bold tracking-widest text-accent uppercase">More than a storefront</p>
        <h2 id="engineering-strip-title" className="text-xl font-extrabold">
          Ten buyers, three units, one click. Watch it refuse to oversell.
        </h2>
      </div>
      <dl className="grid gap-2 sm:grid-cols-3 sm:gap-3">
        {PROOF.map((p) => (
          <div key={p.value} className="flex items-baseline gap-3 rounded-lg bg-white/10 px-3 py-2 sm:grid sm:content-start sm:gap-0.5 sm:py-3">
            <dt className="shrink-0 font-display text-lg font-bold whitespace-nowrap tabular">{p.value}</dt>
            <dd className="text-xs text-white/75">{p.note}</dd>
          </div>
        ))}
      </dl>
      <Link
        to="/how-it-works"
        className="w-fit rounded-lg bg-accent px-4 py-2.5 font-semibold whitespace-nowrap text-ink hover:bg-accent-soft"
      >
        See how it's built →
      </Link>
    </section>
  )
}
