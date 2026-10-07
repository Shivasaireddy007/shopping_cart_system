// Catalog load test.
//
//   k6 run -e BASE_URL=http://127.0.0.1:8000 -e RATE=150 benchmarks/catalog.js
//
// Traffic is shaped like a real shop rather than spread evenly:
// - 70% listing pages, 30% product pages
// - popular categories and products get most of the views (power-law picks)
// - most shoppers stay on page 1; some go a few pages deep
// - some listings add a brand, price range or in-stock filter

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';

export const options = {
    scenarios: {
        browse: {
            // A fixed arrival rate keeps the load identical between runs, so
            // before/after latencies are directly comparable.
            executor: 'constant-arrival-rate',
            rate: Number(__ENV.RATE || 150),
            timeUnit: '1s',
            duration: __ENV.DURATION || '60s',
            preAllocatedVUs: 50,
            maxVUs: 200,
        },
    },
    summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
    thresholds: {
        'http_req_failed': ['rate<0.01'],
        // Listed so k6 reports latency for each endpoint separately.
        'http_req_duration{name:listing}': ['p(95)<2000'],
        'http_req_duration{name:product}': ['p(95)<2000'],
    },
};

const PARAMS = { headers: { Accept: 'application/json' } };

export function setup() {
    const categories = http.get(`${BASE_URL}/api/v1/categories`).json('data').map((c) => c.slug);

    const slugs = [];
    for (let page = 1; page <= 20; page++) {
        const res = http.get(`${BASE_URL}/api/v1/products?per_page=50&page=${page}`);
        res.json('data').forEach((p) => slugs.push(p.slug));
    }

    return { categories, slugs };
}

function pick(list) {
    return list[Math.floor(Math.random() * list.length)];
}

// Picks from the front of the list far more often than the back.
function pickPopular(list) {
    return list[Math.floor(list.length * Math.pow(Math.random(), 3))];
}

function chance(p) {
    return Math.random() < p;
}

const SORT_WEIGHTS = [['newest', 0.5], ['price_asc', 0.2], ['price_desc', 0.2], ['name', 0.1]];
const PRICE_RANGES = [[0, 50000], [50000, 100000], [100000, 300000], [300000, 1000000]];
const BRANDS = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Bata', 'Woodland', 'Campus', 'Sparx'];

function pickSort() {
    let r = Math.random();
    for (const [sort, weight] of SORT_WEIGHTS) {
        if ((r -= weight) < 0) return sort;
    }
    return 'newest';
}

function listingQuery(categories) {
    const params = [`sort=${pickSort()}`, `page=${chance(0.6) ? 1 : 2 + Math.floor(Math.random() * 4)}`];

    if (chance(0.7)) params.push(`category=${pickPopular(categories)}`);
    if (chance(0.15)) params.push(`brand=${pick(BRANDS)}`);
    if (chance(0.15)) {
        const [min, max] = pick(PRICE_RANGES);
        params.push(`min_price=${min}`, `max_price=${max}`);
    }
    if (chance(0.25)) params.push('in_stock=1');

    return params.join('&');
}

export default function (data) {
    if (chance(0.7)) {
        const res = http.get(`${BASE_URL}/api/v1/products?${listingQuery(data.categories)}`, Object.assign({ tags: { name: 'listing' } }, PARAMS));
        check(res, { 'listing 200': (r) => r.status === 200 });
    } else {
        const res = http.get(`${BASE_URL}/api/v1/products/${pickPopular(data.slugs)}`, Object.assign({ tags: { name: 'product' } }, PARAMS));
        check(res, { 'product 200': (r) => r.status === 200 });
    }
}
