<?php

namespace App\Services\Search;

final class SearchResult
{
    /**
     * @param  array<int, int>  $ids  Product ids in ranking order
     * @param  array<string, array<int, array{value: string, count: int}>>  $facets
     */
    public function __construct(
        public readonly array $ids,
        public readonly int $total,
        public readonly array $facets,
    ) {}
}
