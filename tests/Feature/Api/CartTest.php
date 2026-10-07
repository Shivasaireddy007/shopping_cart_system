<?php

namespace Tests\Feature\Api;

use App\Models\Product;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CartTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
        $this->withToken($this->jwtFor($this->user));
    }

    public function test_cart_requires_authentication(): void
    {
        $this->withToken('invalid')->getJson('/api/v1/cart')->assertUnauthorized();
    }

    public function test_adding_the_same_product_twice_increments_quantity(): void
    {
        $product = Product::factory()->create(['price' => 50000, 'stock' => 10]);

        $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 1])->assertOk();
        $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 2])
            ->assertOk()
            ->assertJsonCount(1, 'data.items')
            ->assertJsonPath('data.items.0.quantity', 3)
            ->assertJsonPath('data.subtotal', 150000);
    }

    public function test_shipping_is_free_above_threshold(): void
    {
        config(['commerce.shipping.free_above' => 100000, 'commerce.shipping.flat_fee' => 4900]);
        $cheap = Product::factory()->create(['price' => 50000]);
        $expensive = Product::factory()->create(['price' => 150000]);

        $this->postJson('/api/v1/cart/items', ['product_id' => $cheap->id, 'quantity' => 1])
            ->assertJsonPath('data.shipping_fee', 4900)
            ->assertJsonPath('data.total', 54900);

        $this->postJson('/api/v1/cart/items', ['product_id' => $expensive->id, 'quantity' => 1])
            ->assertJsonPath('data.shipping_fee', 0)
            ->assertJsonPath('data.total', 200000);
    }

    public function test_cannot_add_more_than_available_stock(): void
    {
        $product = Product::factory()->create(['stock' => 2]);

        $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 3])
            ->assertStatus(409)
            ->assertJsonPath('available', 2);
    }

    public function test_cannot_add_inactive_product(): void
    {
        $product = Product::factory()->inactive()->create();

        $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 1])->assertNotFound();
    }

    public function test_quantity_can_be_updated_and_item_removed(): void
    {
        $product = Product::factory()->create(['stock' => 10]);
        $itemId = $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 1])
            ->json('data.items.0.id');

        $this->patchJson("/api/v1/cart/items/{$itemId}", ['quantity' => 4])
            ->assertJsonPath('data.items.0.quantity', 4);

        $this->deleteJson("/api/v1/cart/items/{$itemId}")
            ->assertOk()
            ->assertJsonCount(0, 'data.items');
    }

    public function test_cannot_modify_another_users_cart_item(): void
    {
        $product = Product::factory()->create(['stock' => 10]);
        $itemId = $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 1])
            ->json('data.items.0.id');

        $this->withToken($this->jwtFor(User::factory()->create()))
            ->patchJson("/api/v1/cart/items/{$itemId}", ['quantity' => 2])
            ->assertNotFound();
    }

    public function test_cart_can_be_cleared(): void
    {
        $product = Product::factory()->create();
        $this->postJson('/api/v1/cart/items', ['product_id' => $product->id, 'quantity' => 1]);

        $this->deleteJson('/api/v1/cart')->assertNoContent();
        $this->getJson('/api/v1/cart')->assertJsonCount(0, 'data.items');
    }
}
