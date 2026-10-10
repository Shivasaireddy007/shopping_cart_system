<?php

namespace Tests\Feature\Api;

use App\Enums\OrderStatus;
use App\Models\Product;
use App\Models\User;
use Tests\Concerns\PlacesOrders;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class OrderCancellationTest extends TestCase
{
    use PlacesOrders, RefreshesDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        $this->fakeRazorpay();
    }

    public function test_customer_can_cancel_unpaid_order_and_stock_is_restored(): void
    {
        $user = User::factory()->create();
        $product = Product::factory()->create(['stock' => 5]);
        $order = $this->placeOrder($user, [[$product, 2]]);
        $this->assertSame(3, $product->fresh()->stock);

        $this->withToken($this->jwtFor($user))->postJson("/api/v1/orders/{$order->number}/cancel")
            ->assertOk()
            ->assertJsonPath('data.status', 'cancelled');

        $this->assertSame(5, $product->fresh()->stock);
    }

    public function test_paid_order_cannot_be_cancelled(): void
    {
        $user = User::factory()->create();
        $order = $this->placeOrder($user, [[Product::factory()->create(), 1]]);
        $order->update(['status' => OrderStatus::Paid, 'paid_at' => now()]);

        $this->withToken($this->jwtFor($user))->postJson("/api/v1/orders/{$order->number}/cancel")
            ->assertStatus(409);
    }

    public function test_expire_command_cancels_only_stale_unpaid_orders(): void
    {
        $user = User::factory()->create();
        $product = Product::factory()->create(['stock' => 10]);
        $stale = $this->placeOrder($user, [[$product, 2]]);
        $fresh = $this->placeOrder($user, [[$product, 3]]);
        $stale->forceFill(['created_at' => now()->subHour()])->save();

        $this->artisan('orders:expire-unpaid', ['--minutes' => 30])->assertSuccessful();

        $this->assertSame(OrderStatus::Cancelled, $stale->fresh()->status);
        $this->assertSame(OrderStatus::PendingPayment, $fresh->fresh()->status);
        $this->assertSame(7, $product->fresh()->stock);
    }
}
