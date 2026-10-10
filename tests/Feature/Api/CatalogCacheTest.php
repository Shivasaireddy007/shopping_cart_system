<?php

namespace Tests\Feature\Api;

use App\Models\Product;
use App\Services\Catalog\CatalogCache;
use App\Services\Catalog\HotProducts;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Redis;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class CatalogCacheTest extends TestCase
{
    use RefreshesDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        Redis::connection('cache')->flushdb();
    }

    public function test_listing_is_served_from_cache_until_a_product_changes(): void
    {
        $product = Product::factory()->create();
        $this->getJson('/api/v1/products')->assertJsonPath('meta.total', 1);

        // A raw insert bypasses the observer, so the cached page is still served.
        DB::table('products')->insert(array_merge(
            Product::factory()->raw(['category_id' => $product->category_id]),
            ['attributes' => '{}', 'created_at' => now(), 'updated_at' => now()],
        ));
        $this->getJson('/api/v1/products')->assertJsonPath('meta.total', 1);

        // A model update bumps the catalog version and retires cached listings.
        $product->update(['name' => 'Renamed']);
        $this->getJson('/api/v1/products')->assertJsonPath('meta.total', 2);
    }

    public function test_product_detail_is_invalidated_on_price_change(): void
    {
        $product = Product::factory()->create(['price' => 10000]);
        $this->getJson("/api/v1/products/{$product->slug}")->assertJsonPath('data.price', 10000);

        $product->update(['price' => 12000]);

        $this->getJson("/api/v1/products/{$product->slug}")->assertJsonPath('data.price', 12000);
    }

    public function test_stock_change_inside_a_transaction_invalidates_after_commit(): void
    {
        $product = Product::factory()->create(['stock' => 5]);
        $this->getJson("/api/v1/products/{$product->slug}")->assertJsonPath('data.stock', 5);

        DB::transaction(fn () => $product->decrement('stock', 5));

        $this->getJson("/api/v1/products/{$product->slug}")
            ->assertJsonPath('data.stock', 0)
            ->assertJsonPath('data.in_stock', false);
    }

    public function test_cache_can_be_disabled(): void
    {
        config(['commerce.catalog_cache.enabled' => false]);
        $product = Product::factory()->create(['price' => 10000]);
        $this->getJson("/api/v1/products/{$product->slug}");

        DB::table('products')->where('id', $product->id)->update(['price' => 15000]);

        $this->getJson("/api/v1/products/{$product->slug}")->assertJsonPath('data.price', 15000);
    }

    public function test_views_are_counted_and_hot_products_ranked(): void
    {
        [$a, $b, $c] = Product::factory()->count(3)->create();

        foreach ([$b, $b, $b, $a, $a, $c] as $product) {
            Cache::forget('catalog:product:'.$product->slug);
            $this->getJson("/api/v1/products/{$product->slug}")->assertOk();
        }

        $this->assertSame([$b->id, $a->id], app(HotProducts::class)->top(2));
    }

    public function test_warm_command_pre_caches_hot_products_with_longer_ttl(): void
    {
        config(['commerce.catalog_cache.hot_count' => 1]);
        [$hot, $cold] = Product::factory()->count(2)->create();
        app(HotProducts::class)->recordView($hot->id);
        app(HotProducts::class)->recordView($hot->id);
        app(HotProducts::class)->recordView($cold->id);

        $this->artisan('catalog:warm-hot')->expectsOutput('Warmed 1 hot product(s).')->assertSuccessful();

        $cache = app(CatalogCache::class);
        $this->assertTrue($cache->isHot($hot->slug));
        $this->assertFalse($cache->isHot($cold->slug));
        $this->assertSame($hot->id, Cache::get('catalog:product:'.$hot->slug)['data']['id']);
    }
}
