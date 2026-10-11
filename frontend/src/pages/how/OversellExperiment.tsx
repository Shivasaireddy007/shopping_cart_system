import { useOversellExperiment } from '../../hooks/queries'

const ms = (value: number) => `${Math.round(value)} ms`

/** Ten simultaneous checkouts for three units, run on the server, with and without row locking. */
export function OversellExperiment({ available }: { available: boolean }) {
  const experiment = useOversellExperiment()
  const result = experiment.data

  if (!available) {
    return (
      <p className="text-sm text-muted">
        The live experiment runs on the public demo. Locally, the same check is a test:{' '}
        <code className="font-mono">pytest -m concurrency</code>.
      </p>
    )
  }

  const oversold = result ? result.sold - result.units : 0

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => experiment.mutate(true)}
          disabled={experiment.isPending}
          className="rounded-lg bg-brand px-4 py-2.5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
        >
          Run the real checkout
        </button>
        <button
          type="button"
          onClick={() => experiment.mutate(false)}
          disabled={experiment.isPending}
          className="rounded-lg border border-line bg-surface px-4 py-2.5 font-semibold hover:border-crit hover:text-crit disabled:opacity-60"
        >
          Run naive code without a lock
        </button>
      </div>

      {experiment.isPending ? <p className="text-sm text-muted" role="status">Ten buyers are checking out…</p> : null}
      {experiment.isError ? (
        <p className="rounded-lg bg-crit-soft p-3 text-sm text-crit" role="alert">{experiment.error.message}</p>
      ) : null}

      {result && !experiment.isPending ? (
        <div className="grid gap-3" aria-live="polite">
          <p
            className={`rounded-lg p-3 text-sm font-semibold ${result.locked ? 'bg-good-soft text-good' : 'bg-crit-soft text-crit'}`}
          >
            {result.locked
              ? `${result.sold} of 10 bought, ${10 - result.sold} were told it's sold out, and the stock is ${result.final_stock}. Every unit accounted for.`
              : `${result.sold} of 10 "bought" just ${result.units} units, yet the stock still says ${result.final_stock}. Oversold by ${oversold}: two requests read the same stock and both wrote it back.`}
          </p>
          <ol className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {result.attempts.map((a) => (
              <li
                key={a.buyer}
                className={`grid gap-0.5 rounded-lg border p-2 text-xs ${a.sold ? (result.locked ? 'border-good bg-good-soft' : 'border-crit bg-crit-soft') : 'border-line bg-surface-2'}`}
              >
                <span className="font-semibold">Buyer {a.buyer}</span>
                <span className={a.sold ? (result.locked ? 'text-good' : 'text-crit') : 'text-muted'}>
                  {a.sold ? 'Bought' : 'Sold out'}
                </span>
                <span className="text-muted tabular">{ms(a.ms)}</span>
              </li>
            ))}
          </ol>
          <p className="text-xs text-muted">
            All ten started together on separate database connections and finished in {ms(result.ms)}. The test
            product, buyers and orders were deleted afterwards.
          </p>
        </div>
      ) : null}
    </div>
  )
}
