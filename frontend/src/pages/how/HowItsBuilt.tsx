import type { ReactNode } from 'react'

import { useSystemStats } from '../../hooks/queries'
import { Architecture } from './Architecture'
import { LoadTest } from './LoadTest'
import { OversellExperiment } from './OversellExperiment'

const REPO = 'https://github.com/Shivasaireddy007/shopping_cart_system'
const STACK = ['FastAPI', 'React + TypeScript', 'PostgreSQL', 'Redis', 'Kafka', 'OpenSearch', 'Razorpay', 'Docker', 'Kubernetes']

const DECISIONS = [
  {
    title: 'No overselling',
    body: 'Checkout locks the product rows (SELECT … FOR UPDATE) in id order, so simultaneous checkouts queue instead of racing, and can never deadlock each other.',
    proof: 'backend/tests/test_concurrency.py',
  },
  {
    title: 'Payments recorded exactly once',
    body: "Razorpay's callback and webhook can both arrive, repeat or come out of order. Signatures are HMAC-checked in constant time and each event is de-duplicated in the same transaction as its effect.",
    proof: 'backend/tests/test_payments.py',
  },
  {
    title: 'Events that are never lost',
    body: 'Order and product events are written to an outbox table in the same transaction as the change. A relay publishes them to Kafka, so a crash can neither lose an event nor send one for a rolled-back change.',
    proof: 'backend/tests/test_outbox.py',
  },
  {
    title: 'Workers that act once',
    body: 'Kafka delivers at least once. Each consumer records handled event ids with its effect, retries with backoff and moves failures to a dead-letter topic.',
    proof: 'backend/tests/test_kafka_integration.py',
  },
  {
    title: 'Search that behaves like a real shop',
    body: "Fuzzy text search with facets that keep their counts as you filter, rebuilt with zero downtime by swapping an index alias. If OpenSearch is down, search falls back to PostgreSQL, as in this demo.",
    proof: 'backend/tests/test_search.py',
  },
  {
    title: "Caches that can't go stale",
    body: 'Only changes that actually commit clear the Redis cache. Listing keys carry a catalog version, so one change retires every cached page without scanning keys.',
    proof: 'backend/tests/test_cache.py',
  },
]

const CI_JOBS = [
  'Backend: ruff, mypy (strict), migrations check, pytest against PostgreSQL, Redis, OpenSearch and Kafka',
  'Frontend: generated API types up to date, type check, lint, Vitest',
  'Full stack in Docker Compose with a Playwright test of a whole purchase',
  'Helm chart installed into a Kubernetes cluster (kind) and smoke-tested',
  'Server setup script run on a fresh machine, served over HTTPS',
  "This demo's container built and used to make a purchase",
]

function Section({ id, title, intro, children }: { id: string; title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="grid gap-4 rounded-xl border border-line bg-surface p-5 sm:p-6">
      <div className="grid gap-1">
        <h2 id={id} className="text-xl font-extrabold">{title}</h2>
        {intro ? <p className="max-w-3xl text-sm text-muted">{intro}</p> : null}
      </div>
      {children}
    </section>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="grid content-start gap-1 rounded-lg bg-surface-2 p-3">
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className="text-2xl font-bold tabular">{value}</dd>
      {note ? <dd className="text-xs text-muted">{note}</dd> : null}
    </div>
  )
}

function duration(seconds: number): string {
  if (seconds < 120) return `${seconds} s`
  if (seconds < 7200) return `${Math.floor(seconds / 60)} min`
  return `${Math.floor(seconds / 3600)} h`
}

const timeAgo = (iso: string) => duration(Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))) + ' ago'

function LiveStats() {
  const { data, isError } = useSystemStats()
  if (isError) return <p className="text-sm text-crit">Couldn't reach the server.</p>
  if (!data) return <p className="text-sm text-muted">Loading…</p>

  const { latency, cache } = data
  return (
    <div className="grid gap-4">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label="API latency, p95"
          value={latency.p95_ms != null ? `${latency.p95_ms} ms` : '–'}
          note={latency.p50_ms != null ? `median ${latency.p50_ms} ms · last ${latency.requests} requests` : 'Browse the shop to generate traffic'}
        />
        <Stat
          label="Redis cache hit rate"
          value={cache.hit_rate != null ? `${Math.round(cache.hit_rate * 100)}%` : '–'}
          note={`${cache.hits} hits, ${cache.misses} misses`}
        />
        <Stat label="Products" value={data.products.toLocaleString('en-IN')} note={`${data.orders} orders in the database`} />
        <Stat
          label="Events in the outbox"
          value={data.outbox_events.toLocaleString('en-IN')}
          note={data.outbox_events ? 'Written in the same transaction as each change' : 'Pay for an order to write one'}
        />
      </dl>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="grid content-start gap-2">
          <h3 className="text-sm font-bold">Latest events written</h3>
          {data.recent_events.length ? (
            <ol className="grid gap-1 text-xs">
              {data.recent_events.map((e, i) => (
                <li key={i} className="flex justify-between gap-3 rounded bg-surface-2 px-2 py-1.5">
                  <span className="font-mono">{e.event_type}</span>
                  <span className="text-muted">topic {e.topic} · {timeAgo(e.created_at)}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-xs text-muted">None yet. Place an order or edit a product as the admin.</p>
          )}
          {data.demo ? (
            <p className="text-xs text-muted">In the full stack a relay publishes these to Kafka; this free demo keeps them in PostgreSQL.</p>
          ) : null}
        </div>
        <dl className="grid content-start gap-1 text-xs">
          <h3 className="mb-1 text-sm font-bold">This server</h3>
          {[
            ['Up for', duration(data.uptime_seconds)],
            ['Python', data.python],
            ['PostgreSQL', data.postgres],
            ['Redis', data.redis ?? 'unavailable'],
            ['Commit', data.commit ?? 'local build'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-line py-1">
              <dt className="text-muted">{k}</dt>
              <dd className="font-mono">{v}</dd>
            </div>
          ))}
          <p className="mt-1 text-muted">Refreshes every 5 seconds.</p>
        </dl>
      </div>
    </div>
  )
}

export function HowItsBuilt() {
  const { data } = useSystemStats()

  return (
    <div className="mx-auto grid max-w-5xl gap-6">
      <header className="grid gap-3 py-2">
        <p className="text-xs font-bold tracking-widest text-accent uppercase">How it's built</p>
        <h1 className="text-3xl font-extrabold sm:text-4xl">An order system built for what goes wrong in production</h1>
        <p className="max-w-3xl text-muted">
          The storefront is the easy part. Underneath, this shop handles simultaneous buyers, duplicate payment
          callbacks, crashed workers and traffic spikes. You can try the hardest of those live on this page.
        </p>
        <ul className="flex flex-wrap gap-2" aria-label="Tech stack">
          {STACK.map((s) => (
            <li key={s} className="rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold">{s}</li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-4 text-sm font-semibold">
          <a href={REPO} className="text-brand hover:underline">Source code on GitHub</a>
          <a href="/docs" className="text-brand hover:underline">Interactive API docs</a>
          <a href={`${REPO}/actions`} className="text-brand hover:underline">CI runs</a>
        </div>
      </header>

      <Section
        id="experiment-title"
        title="Try to oversell it"
        intro="Ten buyers press Pay at the same moment for the last three pairs. Run the real checkout, then the same purchase written the naive way, and compare."
      >
        <OversellExperiment available={data?.demo ?? true} />
      </Section>

      <Section
        id="live-title"
        title="Live from this server"
        intro="Real numbers from the running API. Open the Live API requests panel at the bottom right to see individual calls, and whether Redis served them."
      >
        <LiveStats />
      </Section>

      <Section id="arch-title-section" title="Architecture" intro="Every write and its event commit together; everything after that happens asynchronously, retried until it succeeds.">
        <Architecture />
      </Section>

      <Section id="load-title" title="Load tested" intro="What the Redis cache is worth under load.">
        <LoadTest />
      </Section>

      <Section id="decisions-title" title="Design decisions, each backed by a test">
        <ul className="grid gap-3 sm:grid-cols-2">
          {DECISIONS.map((d) => (
            <li key={d.title} className="grid content-start gap-1.5 rounded-lg bg-surface-2 p-4">
              <h3 className="font-bold">{d.title}</h3>
              <p className="text-sm text-muted">{d.body}</p>
              <a href={`${REPO}/blob/master/${d.proof}`} className="font-mono text-xs font-semibold text-brand hover:underline">
                {d.proof.split('/').pop()}
              </a>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="ci-title" title="Checked on every push" intro="Six CI jobs must pass before anything merges.">
        <ol className="grid gap-2 text-sm">
          {CI_JOBS.map((job, i) => (
            <li key={job} className="flex gap-3">
              <span className="font-mono text-xs font-bold text-good tabular">✓ {i + 1}</span>
              <span>{job}</span>
            </li>
          ))}
        </ol>
        <a href={`${REPO}/actions/workflows/ci.yml`} className="w-fit">
          <img src={`${REPO}/actions/workflows/ci.yml/badge.svg`} alt="CI status" height={20} />
        </a>
      </Section>
    </div>
  )
}
