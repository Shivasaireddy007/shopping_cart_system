import { useTracking } from '../hooks/queries'

const STEPS = ['paid', 'shipped', 'delivered'] as const
const STEP_LABELS = { paid: 'Paid', shipped: 'Shipped', delivered: 'Delivered' }

export function Tracking({ number, status }: { number: string; status: string }) {
  const reached = STEPS.indexOf(status as (typeof STEPS)[number])
  const { data } = useTracking(number, reached >= 0)
  if (reached < 0) return null

  return (
    <section className="grid gap-4 rounded-xl bg-surface p-5" aria-labelledby="tracking-title">
      <h2 id="tracking-title" className="text-lg font-bold">Delivery</h2>
      <ol className="grid grid-cols-3 text-center text-sm">
        {STEPS.map((step, i) => (
          <li key={step} className="relative grid justify-items-center gap-1.5">
            {i > 0 ? <span className={`absolute top-2.5 right-1/2 h-0.5 w-full ${i <= reached ? 'bg-good' : 'bg-line'}`} aria-hidden="true" /> : null}
            <span className={`relative z-10 size-5 rounded-full border-[3px] ${i <= reached ? 'border-good bg-good' : 'border-line bg-surface'}`} aria-hidden="true" />
            <span className={i <= reached ? 'font-semibold' : 'text-muted'}>{STEP_LABELS[step]}</span>
          </li>
        ))}
      </ol>
      {data?.awb_code ? (
        <>
          <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <div><dt className="text-muted">Courier</dt><dd className="font-semibold">{data.courier_name}</dd></div>
            <div><dt className="text-muted">AWB</dt><dd className="font-mono font-semibold">{data.awb_code}</dd></div>
            {data.track_url ? (
              <div><dt className="text-muted">Live tracking</dt><dd><a href={data.track_url} target="_blank" rel="noreferrer" className="font-semibold text-brand">Open courier page</a></dd></div>
            ) : null}
          </dl>
          {data.events.length ? (
            <ol className="grid gap-3 border-l-2 border-line pl-4">
              {data.events.map((e, i) => (
                <li key={`${e.date}-${i}`} className="relative grid gap-0.5 text-sm">
                  <span className={`absolute top-1.5 -left-[22px] size-2.5 rounded-full ${i === 0 ? 'bg-good' : 'bg-line'}`} aria-hidden="true" />
                  <span className="font-semibold">{e.activity}{e.location ? ` · ${e.location}` : ''}</span>
                  <time className="text-xs text-muted">{e.date}</time>
                </li>
              ))}
            </ol>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-muted">We're handing your order to a courier. Tracking appears here once it's assigned.</p>
      )}
    </section>
  )
}
