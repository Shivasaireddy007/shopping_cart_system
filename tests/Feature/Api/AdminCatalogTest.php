<?php

namespace Tests\Feature\Api;

use App\Models\Category;
use App\Models\Product;
use App\Models\User;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class AdminCatalogTest extends TestCase
{
    use RefreshesDatabase;

    private function asAdmin(): static
    {
        return $this->withToken($this->jwtFor(User::factory()->admin()->create()));
    }

    private function productPayload(array $overrides = []): array
    {
        return array_merge([
            'category_id' => Category::factory()->create()->id,
            'sku' => 'NIKE-AIR-42',
            'name' => 'Air Zoom Pegasus',
            'brand' => 'Nike',
            'price' => 899900,
            'mrp' => 1099900,
            'stock' => 25,
            'attributes' => ['color' => 'black', 'size' => '42'],
        ], $overrides);
    }

    public function test_customers_cannot_manage_the_catalog(): void
    {
        $this->withToken($this->jwtFor(User::factory()->create()))
            ->postJson('/api/v1/admin/products', $this->productPayload())
            ->assertForbidden();
    }

    public function test_guests_are_rejected(): void
    {
        $this->getJson('/api/v1/admin/products')->assertUnauthorized();
    }

    public function test_admin_can_create_a_product_with_generated_slug(): void
    {
        $response = $this->asAdmin()->postJson('/api/v1/admin/products', $this->productPayload())
            ->assertCreated()
            ->assertJsonPath('data.sku', 'NIKE-AIR-42')
            ->assertJsonPath('data.price', 899900);

        $this->assertStringStartsWith('air-zoom-pegasus-', $response->json('data.slug'));
        $this->getJson('/api/v1/products/'.$response->json('data.slug'))->assertOk();
    }

    public function test_validates_product_fields(): void
    {
        Product::factory()->create(['sku' => 'TAKEN']);

        $this->asAdmin()->postJson('/api/v1/admin/products', $this->productPayload([
            'sku' => 'TAKEN',
            'price' => 50,
            'mrp' => 10,
            'stock' => -1,
        ]))->assertJsonValidationErrors(['sku', 'price', 'mrp', 'stock']);
    }

    public function test_admin_can_update_price_and_stock(): void
    {
        $product = Product::factory()->create(['price' => 10000, 'stock' => 1]);

        $this->asAdmin()->patchJson("/api/v1/admin/products/{$product->id}", ['price' => 12000, 'stock' => 40])
            ->assertOk()
            ->assertJsonPath('data.price', 12000)
            ->assertJsonPath('data.stock', 40);

        $this->getJson("/api/v1/products/{$product->slug}")->assertJsonPath('data.price', 12000);
    }

    public function test_deleting_a_product_archives_it(): void
    {
        $product = Product::factory()->create();

        $this->asAdmin()->deleteJson("/api/v1/admin/products/{$product->id}")
            ->assertOk()
            ->assertJsonPath('data.is_active', false);

        $this->assertDatabaseHas('products', ['id' => $product->id, 'is_active' => false]);
        $this->getJson("/api/v1/products/{$product->slug}")->assertNotFound();
    }

    public function test_admin_listing_includes_inactive_products_and_searches_by_sku(): void
    {
        Product::factory()->inactive()->create(['sku' => 'OLD-1']);
        Product::factory()->create();

        $this->asAdmin()->getJson('/api/v1/admin/products')->assertJsonCount(2, 'data');
        $this->asAdmin()->getJson('/api/v1/admin/products?search=OLD-1')->assertJsonCount(1, 'data');
    }

    public function test_admin_can_manage_categories(): void
    {
        $id = $this->asAdmin()->postJson('/api/v1/admin/categories', ['name' => 'Running Shoes'])
            ->assertCreated()
            ->assertJsonPath('data.slug', 'running-shoes')
            ->json('data.id');

        $this->asAdmin()->patchJson("/api/v1/admin/categories/{$id}", ['name' => 'Running'])
            ->assertJsonPath('data.name', 'Running');

        $this->asAdmin()->deleteJson("/api/v1/admin/categories/{$id}")->assertNoContent();
    }

    public function test_category_with_products_cannot_be_deleted(): void
    {
        $product = Product::factory()->create();

        $this->asAdmin()->deleteJson("/api/v1/admin/categories/{$product->category_id}")->assertStatus(409);
    }

    public function test_registration_cannot_grant_admin(): void
    {
        $this->postJson('/api/v1/auth/register', [
            'name' => 'Sneaky',
            'email' => 'sneaky@example.com',
            'password' => 'secret-password',
            'password_confirmation' => 'secret-password',
            'is_admin' => true,
        ])->assertCreated();

        $this->assertFalse(User::where('email', 'sneaky@example.com')->first()->is_admin);
    }

    public function test_make_admin_command(): void
    {
        $user = User::factory()->create();

        $this->artisan('users:make-admin', ['email' => $user->email])->assertSuccessful();
        $this->assertTrue($user->fresh()->is_admin);

        $this->artisan('users:make-admin', ['email' => $user->email, '--revoke' => true])->assertSuccessful();
        $this->assertFalse($user->fresh()->is_admin);
    }
}
