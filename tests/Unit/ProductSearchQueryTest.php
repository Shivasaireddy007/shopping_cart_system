<?php

namespace Tests\Unit;

use App\Services\Search\ProductSearch;
use Tests\TestCase;

class ProductSearchQueryTest extends TestCase
{
    private function query(array $params): array
    {
        return app(ProductSearch::class)->buildQuery($params);
    }

    public function test_facet_selections_go_to_post_filter_not_main_query(): void
    {
        $query = $this->query(['brand' => ['Nike'], 'color' => ['red']]);

        $this->assertSame([], $query['query']['bool']['filter']);
        $this->assertEqualsCanonicalizing(
            [['terms' => ['brand' => ['Nike']]], ['terms' => ['color' => ['red']]]],
            $query['post_filter']['bool']['filter'],
        );
    }

    public function test_each_facet_aggregation_ignores_its_own_selection(): void
    {
        $query = $this->query(['brand' => ['Nike'], 'color' => ['red']]);

        $this->assertSame([['terms' => ['color' => ['red']]]], $query['aggs']['brand']['filter']['bool']['filter']);
        $this->assertSame([['terms' => ['brand' => ['Nike']]]], $query['aggs']['color']['filter']['bool']['filter']);
        $this->assertCount(2, $query['aggs']['size']['filter']['bool']['filter']);
    }

    public function test_price_and_stock_filters_narrow_everything(): void
    {
        $query = $this->query(['min_price' => 10000, 'max_price' => 50000, 'in_stock' => true]);

        $this->assertContains(['range' => ['price' => ['gte' => 10000, 'lte' => 50000]]], $query['query']['bool']['filter']);
        $this->assertContains(['term' => ['in_stock' => true]], $query['query']['bool']['filter']);
    }

    public function test_text_query_uses_fuzzy_multi_match_and_relevance_sort(): void
    {
        $query = $this->query(['q' => 'running shoe']);

        $this->assertSame('running shoe', $query['query']['bool']['must'][0]['multi_match']['query']);
        $this->assertSame('AUTO', $query['query']['bool']['must'][0]['multi_match']['fuzziness']);
        $this->assertSame('_score', $query['sort'][0]);
    }

    public function test_paginates_with_from_and_size(): void
    {
        $query = $this->query(['page' => 3, 'per_page' => 20]);

        $this->assertSame(40, $query['from']);
        $this->assertSame(20, $query['size']);
    }
}
