<?php

namespace Tests\Concerns;

use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use App\Services\Cart\CartService;
use App\Services\Payments\RazorpayClient;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

trait PlacesOrders
{
    /**
     * Fakes the Razorpay Orders API. Without a fixed id each order gets a
     * unique one, like the real API.
     */
    protected function fakeRazorpay(?string $orderId = null, int $status = 200): void
    {
        config([
            'services.razorpay.key_id' => 'rzp_test_key',
            'services.razorpay.key_secret' => 'key-secret',
            'services.razorpay.webhook_secret' => 'webhook-secret',
        ]);
        $this->app->forgetInstance(RazorpayClient::class);

        Http::fake(['api.razorpay.com/v1/orders' => fn () => Http::response(
            $status === 200 ? ['id' => $orderId ?? 'order_'.Str::random(14)] : ['error' => 'unavailable'],
            $status,
        )]);
    }

    protected function shippingAddress(): array
    {
        return [
            'name' => 'Asha Rao',
            'phone' => '9876543210',
            'line1' => '12 MG Road',
            'city' => 'Bengaluru',
            'state' => 'Karnataka',
            'pincode' => '560001',
        ];
    }

    /**
     * @param  array<int, array{0: Product, 1: int}>  $lines
     */
    protected function placeOrder(User $user, array $lines): Order
    {
        foreach ($lines as [$product, $quantity]) {
            app(CartService::class)->add($user, $product, $quantity);
        }

        $number = $this->withToken($this->jwtFor($user))
            ->postJson('/api/v1/checkout', ['shipping_address' => $this->shippingAddress()])
            ->assertCreated()
            ->json('data.number');

        return Order::where('number', $number)->firstOrFail();
    }
}
