// Catalog and search load test.
//
//   k6 run -e BASE_URL=http://127.0.0.1:8001 -e RATE=300 benchmarks/catalog.js
//
// Traffic is shaped like a shop rather than spread evenly:
// - 55% listing pages, 25% product pages, 20% searches
// - popular categories, products and queries get most of the traffic (power-law picks)
// - most visitors stay on page 1; some add brand, price or in-stock filters
// A fixed arrival rate gives every run identical load, so runs are comparable.

import http from 'k6/http'
import { check } from 'k6'

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8001'
const API = `${BASE_URL}/api/v1`

export const options = {
  scenarios: {
    shoppers: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 300),
      timeUnit: '1s',
      duration: __ENV.DURATION || '60s',
      preAllocatedVUs: 100,
      maxVUs: 400,
    },
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    // Listed so k6 reports each endpoint separately.
    'http_req_duration{name:listing}': ['p(95)<2000'],
    'http_req_duration{name:product}': ['p(95)<2000'],
    'http_req_duration{name:search}': ['p(95)<2000'],
  },
}

const SORTS = [['newest', 0.5], ['price_asc', 0.2], ['price_desc', 0.2], ['name', 0.1]]
const BRANDS = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Bata', 'Woodland', 'Campus', 'Sparx']
const PRICE_RANGES = [[0, 50000], [50000, 100000], [100000, 300000], [300000, 1000000]]
const QUERIES = ['running shoes', 'nike', 'jeans', 'trail', 'jacket', 'sneakers', 'kurta', 'watch', 'urban hoodie', 'formal shoes']

const pick = (list) => list[Math.floor(Math.random() * list.length)]
const pickPopular = (list) => list[Math.floor(list.length * Math.pow(Math.random(), 3))]
const chance = (p) => Math.random() < p

function weighted(pairs) {
  let r = Math.random()
  for (const [value, weight] of pairs) if ((r -= weight) < 0) return value
  return pairs[0][0]
}

export function setup() {
  const categories = http.get(`${API}/categories`).json().map((c) => c.slug)
  const slugs = []
  for (let page = 1; page <= 20; page++) {
    http.get(`${API}/products?per_page=50&page=${page}`).json('items').forEach((p) => slugs.push(p.slug))
  }
  return { categories, slugs }
}

function listingQuery(categories) {
  const params = [`sort=${weighted(SORTS)}`, `page=${chance(0.6) ? 1 : 2 + Math.floor(Math.random() * 4)}`]
  if (chance(0.7)) params.push(`category=${pickPopular(categories)}`)
  if (chance(0.15)) params.push(`brand=${pick(BRANDS)}`)
  if (chance(0.15)) {
    const [min, max] = pick(PRICE_RANGES)
    params.push(`min_price=${min}`, `max_price=${max}`)
  }
  if (chance(0.25)) params.push('in_stock=true')
  return params.join('&')
}

export default function (data) {
  const r = Math.random()
  if (r < 0.55) {
    const res = http.get(`${API}/products?${listingQuery(data.categories)}`, { tags: { name: 'listing' } })
    check(res, { 'listing 200': (x) => x.status === 200 })
  } else if (r < 0.8) {
    const res = http.get(`${API}/products/${pickPopular(data.slugs)}`, { tags: { name: 'product' } })
    check(res, { 'product 200': (x) => x.status === 200 })
  } else {
    const q = encodeURIComponent(pickPopular(QUERIES))
    const brand = chance(0.3) ? `&brand=${pick(BRANDS)}` : ''
    const res = http.get(`${API}/search?q=${q}${brand}`, { tags: { name: 'search' } })
    check(res, { 'search 200': (x) => x.status === 200 && x.json('engine') === 'opensearch' })
  }
}
