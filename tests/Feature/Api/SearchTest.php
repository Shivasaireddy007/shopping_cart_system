<?php

namespace Tests\Feature\Api;

use App\Jobs\SyncProductToSearch;
use App\Models\Product;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class SearchTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        config(['services.elasticsearch.enabled' => true, 'services.elasticsearch.host' => 'http://es.test:9200']);
        Bus::fake([SyncProductToSearch::class]);
    }

    public function test_returns_products_in_search_ranking_order_with_facets(): void
    {
        [$a, $b] = Product::factory()->count(2)->create();

        Http::fake(['es.test:9200/products/_search' => Http::response([
            'hits' => ['total' => ['value' => 2], 'hits' => [['_id' => (string) $b->id], ['_id' => (string) $a->id]]],
            'aggregations' => [
                'brand' => ['values' => ['buckets' => [['key' => 'Nike', 'doc_count' => 7], ['key' => 'Puma', 'doc_count' => 3]]]],
                'category' => ['values' => ['buckets' => []]],
                'color' => ['values' => ['buckets' => [['key' => 'red', 'doc_count' => 2]]]],
                'size' => ['values' => ['buckets' => []]],
                'price' => ['ranges' => ['buckets' => [['key' => 'under-500', 'doc_count' => 1]]]],
            ],
        ])]);

        $this->getJson('/api/v1/search?q=shoe&brand[]=Nike')
            ->assertOk()
            ->assertJsonPath('meta.engine', 'elasticsearch')
            ->assertJsonPath('meta.total', 2)
            ->assertJsonPath('data.0.id', $b->id)
            ->assertJsonPath('data.1.id', $a->id)
            ->assertJsonPath('facets.brand.0', ['value' => 'Nike', 'count' => 7])
            ->assertJsonPath('facets.price.0.value', 'under-500');

        Http::assertSent(fn ($request) => $request['post_filter']['bool']['filter'] === [['terms' => ['brand' => ['Nike']]]]);
    }

    public function test_falls_back_to_database_when_elasticsearch_is_down(): void
    {
        Product::factory()->create(['brand' => 'Nike']);
        Product::factory()->create(['brand' => 'Puma']);

        Http::fake(['es.test:9200/*' => fn () => throw new ConnectionException('Connection refused')]);

        $this->getJson('/api/v1/search?brand[]=Nike')
            ->assertOk()
            ->assertJsonPath('meta.engine', 'database')
            ->assertJsonPath('facets', null)
            ->assertJsonCount(1, 'data');
    }

    public function test_validates_filters(): void
    {
        $this->getJson('/api/v1/search?brand=Nike&per_page=100')
            ->assertJsonValidationErrors(['brand', 'per_page']);
    }

    public function test_saving_a_product_queues_a_search_sync(): void
    {
        $product = Product::factory()->create();

        Bus::assertDispatched(SyncProductToSearch::class, fn ($job) => $job->productId === $product->id);
    }

    public function test_sync_job_indexes_active_and_removes_inactive_products(): void
    {
        Http::fake(['es.test:9200/*' => Http::response(['result' => 'ok'])]);
        $active = Product::factory()->create();
        $inactive = Product::factory()->inactive()->create();

        (new SyncProductToSearch($active->id))->handle(app(\App\Services\Search\ProductIndex::class));
        (new SyncProductToSearch($inactive->id))->handle(app(\App\Services\Search\ProductIndex::class));

        Http::assertSent(fn ($r) => $r->method() === 'PUT' && str_ends_with($r->url(), "/products/_doc/{$active->id}") && $r['sku'] === $active->sku);
        Http::assertSent(fn ($r) => $r->method() === 'DELETE' && str_ends_with($r->url(), "/products/_doc/{$inactive->id}"));
    }
}
