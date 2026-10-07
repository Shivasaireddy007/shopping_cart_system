<?php

namespace Tests\Feature\Api;

use App\Enums\OrderStatus;
use App\Events\OrderPaid;
use App\Jobs\CreateShipment;
use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use App\Services\Shipping\ShiprocketClient;
use Illuminate\Http\Client\RequestException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Http;
use Tests\Concerns\PlacesOrders;
use Tests\TestCase;

class ShippingTest extends TestCase
{
    use PlacesOrders, RefreshDatabase;

    private User $user;

    private Order $order;

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'services.shiprocket.email' => 'ops@example.com',
            'services.shiprocket.password' => 'secret',
            'services.shiprocket.webhook_token' => 'ship-token',
        ]);
        $this->fakeRazorpay();
        $this->user = User::factory()->create();
        $this->order = $this->placeOrder($this->user, [[Product::factory()->create(['price' => 150000, 'weight_grams' => 750, 'stock' => 10]), 2]]);
        $this->order->update(['status' => OrderStatus::Paid, 'paid_at' => now()]);
    }

    public function test_paid_order_queues_shipment_creation(): void
    {
        Bus::fake([CreateShipment::class]);

        OrderPaid::dispatch($this->order);

        Bus::assertDispatched(CreateShipment::class, fn ($job) => $job->order->is($this->order));
    }

    public function test_job_creates_shiprocket_order_and_assigns_awb(): void
    {
        $this->fakeShiprocket();

        CreateShipment::dispatchSync($this->order);

        $shipment = $this->order->fresh()->shipment;
        $this->assertSame('AWB123', $shipment->awb_code);
        $this->assertSame('Delhivery', $shipment->courier_name);
        $this->assertSame(9001, $shipment->shiprocket_shipment_id);

        Http::assertSent(fn ($request) => str_ends_with($request->url(), '/orders/create/adhoc')
            && $request['order_id'] === $this->order->number
            && $request['payment_method'] === 'Prepaid'
            && $request['weight'] === 1.5
            && $request->hasHeader('Authorization', 'Bearer sr-token'));
    }

    public function test_retry_after_awb_failure_does_not_create_a_second_shiprocket_order(): void
    {
        $this->fakeShiprocket(awbResponses: [
            Http::response(['message' => 'Courier unavailable'], 500),
            Http::response(['response' => ['data' => ['awb_code' => 'AWB123', 'courier_name' => 'Delhivery']]]),
        ]);

        try {
            CreateShipment::dispatchSync($this->order);
            $this->fail('First attempt should fail on AWB assignment.');
        } catch (RequestException) {
        }

        $this->assertNull($this->order->fresh()->shipment->awb_code);

        CreateShipment::dispatchSync($this->order);

        $this->assertSame(1, Http::recorded(fn ($request) => str_ends_with($request->url(), '/orders/create/adhoc'))->count());
        $this->assertSame('AWB123', $this->order->fresh()->shipment->awb_code);
    }

    public function test_webhook_moves_order_forward_and_ignores_out_of_order_updates(): void
    {
        $this->fakeShiprocket();
        CreateShipment::dispatchSync($this->order);

        $this->shiprocketWebhook('AWB123', 'IN TRANSIT')->assertJsonPath('status', 'ok');
        $this->assertSame(OrderStatus::Shipped, $this->order->fresh()->status);

        $this->shiprocketWebhook('AWB123', 'DELIVERED');
        $this->shiprocketWebhook('AWB123', 'OUT FOR DELIVERY'); // arrives late

        $this->assertSame(OrderStatus::Delivered, $this->order->fresh()->status);
    }

    public function test_webhook_requires_the_shared_token(): void
    {
        $this->postJson('/api/webhooks/shiprocket', ['awb' => 'AWB123', 'current_status' => 'DELIVERED'], ['x-api-key' => 'wrong'])
            ->assertUnauthorized();
    }

    public function test_duplicate_webhook_is_ignored(): void
    {
        $this->fakeShiprocket();
        CreateShipment::dispatchSync($this->order);

        $this->shiprocketWebhook('AWB123', 'IN TRANSIT')->assertJsonPath('status', 'ok');
        $this->shiprocketWebhook('AWB123', 'IN TRANSIT')->assertJsonPath('status', 'duplicate');
    }

    public function test_tracking_endpoint_returns_courier_timeline(): void
    {
        $this->fakeShiprocket();
        CreateShipment::dispatchSync($this->order);

        $this->withToken($this->jwtFor($this->user))
            ->getJson("/api/v1/orders/{$this->order->number}/tracking")
            ->assertOk()
            ->assertJsonPath('data.awb_code', 'AWB123')
            ->assertJsonPath('data.events.0.activity', 'Shipment picked up');
    }

    /**
     * @param  array<int, \GuzzleHttp\Promise\PromiseInterface>|null  $awbResponses
     */
    private function fakeShiprocket(?array $awbResponses = null): void
    {
        $this->app->forgetInstance(ShiprocketClient::class);

        $awbResponses ??= [Http::response(['response' => ['data' => ['awb_code' => 'AWB123', 'courier_name' => 'Delhivery']]])];

        Http::fake([
            'api.razorpay.com/*' => Http::response(['id' => 'order_X']),
            '*/auth/login' => Http::response(['token' => 'sr-token']),
            '*/orders/create/adhoc' => Http::response(['order_id' => 5001, 'shipment_id' => 9001, 'status' => 'NEW']),
            '*/courier/assign/awb' => Http::sequence($awbResponses),
            '*/courier/track/awb/*' => Http::response(['tracking_data' => [
                'track_url' => 'https://shiprocket.co/tracking/AWB123',
                'shipment_track_activities' => [['date' => '2026-10-08 10:00:00', 'activity' => 'Shipment picked up']],
            ]]),
        ]);
    }

    private function shiprocketWebhook(string $awb, string $status)
    {
        return $this->postJson('/api/webhooks/shiprocket', [
            'awb' => $awb,
            'current_status' => $status,
            'order_id' => $this->order->number,
        ], ['x-api-key' => 'ship-token']);
    }
}
