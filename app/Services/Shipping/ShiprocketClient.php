<?php

namespace App\Services\Shipping;

use App\Models\Order;
use App\Models\OrderItem;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

/**
 * Client for the Shiprocket external API.
 *
 * @see https://apidocs.shiprocket.in/
 */
class ShiprocketClient
{
    private const TOKEN_CACHE_KEY = 'shiprocket:token';

    public function __construct(
        private readonly string $email,
        private readonly string $password,
        private readonly string $pickupLocation,
        private readonly string $baseUrl,
    ) {}

    public static function fromConfig(): self
    {
        return new self(
            (string) config('services.shiprocket.email'),
            (string) config('services.shiprocket.password'),
            (string) config('services.shiprocket.pickup_location'),
            (string) config('services.shiprocket.base_url'),
        );
    }

    /**
     * Creates a Shiprocket order for a paid order.
     *
     * @return array{order_id: int, shipment_id: int}
     */
    public function createOrder(Order $order): array
    {
        $address = $order->shipping_address;
        [$firstName, $lastName] = array_pad(explode(' ', $address['name'], 2), 2, '');

        $response = $this->send('post', '/orders/create/adhoc', [
            'order_id' => $order->number,
            'order_date' => $order->created_at->format('Y-m-d H:i'),
            'pickup_location' => $this->pickupLocation,
            'billing_customer_name' => $firstName,
            'billing_last_name' => $lastName,
            'billing_address' => $address['line1'],
            'billing_address_2' => $address['line2'] ?? '',
            'billing_city' => $address['city'],
            'billing_pincode' => $address['pincode'],
            'billing_state' => $address['state'],
            'billing_country' => 'India',
            'billing_email' => $order->user->email,
            'billing_phone' => $address['phone'],
            'shipping_is_billing' => true,
            'order_items' => $order->items->map(fn (OrderItem $item) => [
                'name' => $item->name,
                'sku' => $item->sku,
                'units' => $item->quantity,
                'selling_price' => $item->unit_price / 100,
            ])->all(),
            'payment_method' => 'Prepaid',
            'shipping_charges' => $order->shipping_fee / 100,
            'sub_total' => $order->subtotal / 100,
            'length' => 30,
            'breadth' => 20,
            'height' => 10,
            'weight' => max(0.1, $order->totalWeightGrams() / 1000),
        ]);

        return [
            'order_id' => (int) $response->json('order_id'),
            'shipment_id' => (int) $response->json('shipment_id'),
        ];
    }

    /**
     * Assigns a courier and returns the AWB number.
     *
     * @return array{awb_code: string, courier_name: string}
     */
    public function assignAwb(int $shipmentId): array
    {
        $response = $this->send('post', '/courier/assign/awb', ['shipment_id' => $shipmentId]);

        return [
            'awb_code' => (string) $response->json('response.data.awb_code'),
            'courier_name' => (string) $response->json('response.data.courier_name'),
        ];
    }

    /**
     * Returns the tracking timeline for an AWB.
     */
    public function track(string $awb): array
    {
        return $this->send('get', "/courier/track/awb/{$awb}")->json('tracking_data') ?? [];
    }

    private function send(string $method, string $uri, array $data = []): Response
    {
        $response = $this->http()->{$method}($uri, $data);

        // Tokens last 10 days; if one was revoked early, log in again once.
        if ($response->status() === 401) {
            Cache::forget(self::TOKEN_CACHE_KEY);
            $response = $this->http()->{$method}($uri, $data);
        }

        return $response->throw();
    }

    private function http(): PendingRequest
    {
        return Http::baseUrl($this->baseUrl)
            ->withToken($this->token())
            ->acceptJson()
            ->timeout(15);
    }

    private function token(): string
    {
        return Cache::remember(self::TOKEN_CACHE_KEY, now()->addDays(9), function () {
            return Http::baseUrl($this->baseUrl)
                ->acceptJson()
                ->post('/auth/login', ['email' => $this->email, 'password' => $this->password])
                ->throw()
                ->json('token');
        });
    }
}
