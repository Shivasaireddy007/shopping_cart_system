<?php

namespace Tests\Feature\Api;

use App\Models\Category;
use App\Models\Product;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class ProductCatalogTest extends TestCase
{
    use RefreshesDatabase;

    public function test_lists_only_active_products(): void
    {
        Product::factory()->count(3)->create();
        Product::factory()->inactive()->create();

        $this->getJson('/api/v1/products')
            ->assertOk()
            ->assertJsonCount(3, 'data')
            ->assertJsonPath('meta.total', 3);
    }

    public function test_filters_by_category_brand_and_price(): void
    {
        $shoes = Category::factory()->create(['slug' => 'shoes']);
        Product::factory()->for($shoes)->create(['brand' => 'Nike', 'price' => 250000]);
        Product::factory()->for($shoes)->create(['brand' => 'Nike', 'price' => 900000]);
        Product::factory()->for($shoes)->create(['brand' => 'Puma', 'price' => 250000]);
        Product::factory()->create(['brand' => 'Nike', 'price' => 250000]);

        $this->getJson('/api/v1/products?category=shoes&brand=Nike&max_price=500000')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.price', 250000);
    }

    public function test_sorts_by_price(): void
    {
        Product::factory()->create(['price' => 30000]);
        Product::factory()->create(['price' => 10000]);
        Product::factory()->create(['price' => 20000]);

        $prices = $this->getJson('/api/v1/products?sort=price_asc')->json('data.*.price');

        $this->assertSame([10000, 20000, 30000], $prices);
    }

    public function test_rejects_invalid_filters(): void
    {
        $this->getJson('/api/v1/products?sort=random&per_page=500')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['sort', 'per_page']);
    }

    public function test_shows_a_product_by_slug(): void
    {
        $product = Product::factory()->create();

        $this->getJson("/api/v1/products/{$product->slug}")
            ->assertOk()
            ->assertJsonPath('data.sku', $product->sku)
            ->assertJsonPath('data.category.id', $product->category_id);
    }

    public function test_inactive_product_is_not_found(): void
    {
        $product = Product::factory()->inactive()->create();

        $this->getJson("/api/v1/products/{$product->slug}")->assertNotFound();
    }

    public function test_lists_categories(): void
    {
        Category::factory()->count(2)->create();

        $this->getJson('/api/v1/categories')->assertOk()->assertJsonCount(2, 'data');
    }
}
