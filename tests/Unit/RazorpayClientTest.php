<?php

namespace Tests\Unit;

use App\Services\Payments\RazorpayClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class RazorpayClientTest extends TestCase
{
    private RazorpayClient $client;

    protected function setUp(): void
    {
        parent::setUp();

        $this->client = new RazorpayClient('rzp_test_key', 'key-secret', 'webhook-secret', 'https://api.razorpay.com/v1');
    }

    public function test_accepts_a_valid_payment_signature(): void
    {
        $signature = hash_hmac('sha256', 'order_123|pay_456', 'key-secret');

        $this->assertTrue($this->client->isValidPaymentSignature('order_123', 'pay_456', $signature));
    }

    public function test_rejects_a_tampered_payment_signature(): void
    {
        $signature = hash_hmac('sha256', 'order_123|pay_456', 'key-secret');

        $this->assertFalse($this->client->isValidPaymentSignature('order_123', 'pay_999', $signature));
    }

    public function test_verifies_webhook_signature_against_raw_body(): void
    {
        $body = '{"event":"payment.captured"}';

        $this->assertTrue($this->client->isValidWebhookSignature($body, hash_hmac('sha256', $body, 'webhook-secret')));
        $this->assertFalse($this->client->isValidWebhookSignature($body.' ', hash_hmac('sha256', $body, 'webhook-secret')));
    }

    public function test_rejects_webhooks_when_no_secret_is_configured(): void
    {
        $client = new RazorpayClient('key', 'secret', '', 'https://api.razorpay.com/v1');

        $this->assertFalse($client->isValidWebhookSignature('{}', hash_hmac('sha256', '{}', '')));
    }

    public function test_creates_an_order_with_amount_in_paise(): void
    {
        Http::fake(['api.razorpay.com/v1/orders' => Http::response(['id' => 'order_ABC'])]);

        $this->assertSame('order_ABC', $this->client->createOrder(129900, 'ORD-1', ['order_number' => 'ORD-1']));

        Http::assertSent(fn ($request) => $request['amount'] === 129900
            && $request['currency'] === 'INR'
            && $request['receipt'] === 'ORD-1'
            && $request->hasHeader('Authorization', 'Basic '.base64_encode('rzp_test_key:key-secret')));
    }
}
