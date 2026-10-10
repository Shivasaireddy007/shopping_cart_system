<?php

namespace App\Services\Search;

/**
 * Faceted product search on Elasticsearch.
 *
 * Facets are disjunctive: selecting brand=Nike still shows the counts for
 * every other brand. Facet filters therefore go into a post_filter, and each
 * facet's aggregation applies every selected filter except its own.
 */
class ProductSearch
{
    public const FACETS = ['brand', 'category', 'color', 'size'];

    public const PRICE_RANGES = [
        ['key' => 'under-500', 'to' => 50000],
        ['key' => '500-1000', 'from' => 50000, 'to' => 100000],
        ['key' => '1000-2500', 'from' => 100000, 'to' => 250000],
        ['key' => '2500-5000', 'from' => 250000, 'to' => 500000],
        ['key' => 'over-5000', 'from' => 500000],
    ];

    public function __construct(
        private readonly ElasticsearchClient $es,
        private readonly ProductIndex $index,
    ) {}

    /**
     * @param  array{q?: string, brand?: array, category?: array, color?: array, size?: array, min_price?: int, max_price?: int, in_stock?: bool, sort?: string, page?: int, per_page?: int}  $params
     */
    public function search(array $params): SearchResult
    {
        $response = $this->es->post("/{$this->index->alias()}/_search", $this->buildQuery($params))->throw();

        $facets = [];
        foreach (self::FACETS as $facet) {
            $facets[$facet] = collect($response->json("aggregations.{$facet}.values.buckets", []))
                ->map(fn (array $bucket) => ['value' => (string) $bucket['key'], 'count' => $bucket['doc_count']])
                ->all();
        }

        $facets['price'] = collect($response->json('aggregations.price.ranges.buckets', []))
            ->map(fn (array $bucket) => ['value' => $bucket['key'], 'count' => $bucket['doc_count']])
            ->all();

        return new SearchResult(
            ids: array_map('intval', array_column($response->json('hits.hits', []), '_id')),
            total: (int) $response->json('hits.total.value', 0),
            facets: $facets,
        );
    }

    /**
     * @return array<string, mixed>
     */
    public function buildQuery(array $params): array
    {
        $perPage = $params['per_page'] ?? 24;
        $page = $params['page'] ?? 1;
        $selected = $this->facetFilters($params);

        $aggregations = [];
        foreach (self::FACETS as $facet) {
            $aggregations[$facet] = [
                'filter' => $this->allExcept($selected, $facet),
                'aggs' => ['values' => ['terms' => ['field' => $facet, 'size' => 30]]],
            ];
        }
        $aggregations['price'] = [
            'filter' => $this->allExcept($selected, null),
            'aggs' => ['ranges' => ['range' => ['field' => 'price', 'ranges' => self::PRICE_RANGES]]],
        ];

        return [
            'query' => [
                'bool' => [
                    'must' => [$this->textQuery($params['q'] ?? null)],
                    'filter' => $this->baseFilters($params),
                ],
            ],
            'post_filter' => $this->allExcept($selected, null),
            'aggs' => $aggregations,
            'sort' => $this->sort($params['sort'] ?? null, isset($params['q'])),
            'from' => ($page - 1) * $perPage,
            'size' => $perPage,
            'track_total_hits' => true,
            '_source' => false,
        ];
    }

    private function textQuery(?string $q): array
    {
        if ($q === null || trim($q) === '') {
            return ['match_all' => (object) []];
        }

        return [
            'multi_match' => [
                'query' => $q,
                'fields' => ['name^3', 'brand^2', 'description'],
                'fuzziness' => 'AUTO',
                'operator' => 'and',
            ],
        ];
    }

    /**
     * Filters that are not facets narrow everything, including facet counts.
     */
    private function baseFilters(array $params): array
    {
        $filters = [];

        if (isset($params['min_price']) || isset($params['max_price'])) {
            $filters[] = ['range' => ['price' => array_filter([
                'gte' => $params['min_price'] ?? null,
                'lte' => $params['max_price'] ?? null,
            ], fn ($v) => $v !== null)]];
        }

        if (! empty($params['in_stock'])) {
            $filters[] = ['term' => ['in_stock' => true]];
        }

        return $filters;
    }

    /**
     * @return array<string, array<int, string>>
     */
    private function facetFilters(array $params): array
    {
        return collect(self::FACETS)
            ->mapWithKeys(fn (string $facet) => [$facet => array_values((array) ($params[$facet] ?? []))])
            ->filter()
            ->all();
    }

    private function allExcept(array $selected, ?string $exclude): array
    {
        $clauses = [];

        foreach ($selected as $facet => $values) {
            if ($facet !== $exclude) {
                $clauses[] = ['terms' => [$facet => $values]];
            }
        }

        return ['bool' => ['filter' => $clauses]];
    }

    private function sort(?string $sort, bool $hasQuery): array
    {
        return match ($sort) {
            'price_asc' => [['price' => 'asc'], ['id' => 'desc']],
            'price_desc' => [['price' => 'desc'], ['id' => 'desc']],
            'newest' => [['created_at' => 'desc'], ['id' => 'desc']],
            default => $hasQuery ? ['_score', ['id' => 'desc']] : [['created_at' => 'desc'], ['id' => 'desc']],
        };
    }
}
