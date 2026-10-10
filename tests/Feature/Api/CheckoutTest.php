<?php

namespace Tests\Feature\Api;

use App\Enums\OrderStatus;
use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use App\Services\Cart\CartService;
use Tests\Concerns\PlacesOrders;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class CheckoutTest extends TestCase
{
    use PlacesOrders, RefreshesDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
    }

    public function test_checkout_creates_order_reserves_stock_and_returns_razorpay_details(): void
    {
        $this->fakeRazorpay('order_TEST123');
        $product = Product::factory()->create(['price' => 60000, 'stock' => 5]);
        app(CartService::class)->add($this->user, $product, 2);

        $response = $this->withToken($this->jwtFor($this->user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $this->shippingAddress()]);

        $response->assertCreated()
            ->assertJsonPath('data.status', 'pending_payment')
            ->assertJsonPath('data.total', 120000)
            ->assertJsonPath('razorpay.order_id', 'order_TEST123')
            ->assertJsonPath('razorpay.amount', 120000)
            ->assertJsonPath('razorpay.key_id', 'rzp_test_key');

        $this->assertSame(3, $product->fresh()->stock);
        $this->assertSame(0, $this->user->cart->items()->count());
        $this->assertDatabaseHas('order_items', ['sku' => $product->sku, 'quantity' => 2, 'unit_price' => 60000]);
    }

    public function test_order_keeps_price_snapshot_when_product_price_changes(): void
    {
        $this->fakeRazorpay();
        $product = Product::factory()->create(['price' => 50000, 'stock' => 5]);
        $order = $this->placeOrder($this->user, [[$product, 1]]);

        $product->update(['price' => 99900]);

        $this->assertSame(50000, $order->items()->first()->unit_price);
    }

    public function test_checkout_with_empty_cart_is_rejected(): void
    {
        $this->fakeRazorpay();
        $this->withToken($this->jwtFor($this->user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $this->shippingAddress()])
            ->assertUnprocessable();
    }

    public function test_checkout_fails_when_stock_ran_out_after_adding_to_cart(): void
    {
        $this->fakeRazorpay();
        $product = Product::factory()->create(['stock' => 3]);
        app(CartService::class)->add($this->user, $product, 3);
        $product->update(['stock' => 1]);

        $this->withToken($this->jwtFor($this->user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $this->shippingAddress()])
            ->assertStatus(409);

        $this->assertSame(1, $product->fresh()->stock);
        $this->assertSame(0, Order::count());
    }

    public function test_gateway_failure_cancels_order_and_releases_stock(): void
    {
        $this->fakeRazorpay(status: 500);
        $product = Product::factory()->create(['stock' => 4]);
        app(CartService::class)->add($this->user, $product, 2);

        $this->withToken($this->jwtFor($this->user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $this->shippingAddress()])
            ->assertStatus(502);

        $this->assertSame(4, $product->fresh()->stock);
        $this->assertSame(OrderStatus::Cancelled, Order::first()->status);
        $this->assertSame(1, $this->user->cart->items()->count(), 'cart should be kept for a retry');
    }

    public function test_validates_indian_phone_and_pincode(): void
    {
        $this->fakeRazorpay();
        $address = array_merge($this->shippingAddress(), ['phone' => '12345', 'pincode' => '0560']);

        $this->withToken($this->jwtFor($this->user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $address])
            ->assertJsonValidationErrors(['shipping_address.phone', 'shipping_address.pincode']);
    }

    public function test_user_sees_only_their_own_orders(): void
    {
        $this->fakeRazorpay();
        $order = $this->placeOrder($this->user, [[Product::factory()->create(), 1]]);
        $other = User::factory()->create();

        $this->withToken($this->jwtFor($this->user))->getJson('/api/v1/orders')
            ->assertJsonCount(1, 'data');
        $this->withToken($this->jwtFor($other))->getJson("/api/v1/orders/{$order->number}")
            ->assertNotFound();
    }
}
