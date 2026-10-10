<?php

namespace App\Services\Payments;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

/**
 * Thin client for the Razorpay Orders API and signature checks.
 *
 * @see https://razorpay.com/docs/api/orders/
 * @see https://razorpay.com/docs/payments/server-integration/php/payment-gateway/build-integration/#verify-payment-signature
 */
class RazorpayClient
{
    public function __construct(
        private readonly string $keyId,
        private readonly string $keySecret,
        private readonly string $webhookSecret,
        private readonly string $baseUrl,
    ) {}

    public static function fromConfig(): self
    {
        return new self(
            (string) config('services.razorpay.key_id'),
            (string) config('services.razorpay.key_secret'),
            (string) config('services.razorpay.webhook_secret'),
            (string) config('services.razorpay.base_url'),
        );
    }

    public function keyId(): string
    {
        return $this->keyId;
    }

    /**
     * Creates a Razorpay order and returns its id (order_xxx).
     *
     * @param  int  $amount  Amount in paise
     * @param  array<string, string>  $notes
     */
    public function createOrder(int $amount, string $receipt, array $notes = []): string
    {
        $response = $this->http()->post('/orders', [
            'amount' => $amount,
            'currency' => 'INR',
            'receipt' => $receipt,
            'notes' => (object) $notes,
        ])->throw();

        return $response->json('id');
    }

    /**
     * Checks the signature Razorpay Checkout returns after a successful payment.
     */
    public function isValidPaymentSignature(string $orderId, string $paymentId, string $signature): bool
    {
        $expected = hash_hmac('sha256', $orderId.'|'.$paymentId, $this->keySecret);

        return hash_equals($expected, $signature);
    }

    /**
     * Checks the X-Razorpay-Signature header against the raw webhook body.
     */
    public function isValidWebhookSignature(string $payload, string $signature): bool
    {
        if ($this->webhookSecret === '') {
            return false;
        }

        return hash_equals(hash_hmac('sha256', $payload, $this->webhookSecret), $signature);
    }

    private function http(): PendingRequest
    {
        return Http::baseUrl($this->baseUrl)
            ->withBasicAuth($this->keyId, $this->keySecret)
            ->acceptJson()
            ->timeout(10)
            ->retry(2, 200, throw: false);
    }
}
