<?php

namespace Tests\Feature\Api;

use App\Enums\OrderStatus;
use App\Events\OrderPaid;
use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use Illuminate\Support\Facades\Event;
use Tests\Concerns\PlacesOrders;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class PaymentTest extends TestCase
{
    use PlacesOrders, RefreshesDatabase;

    private User $user;

    private Order $order;

    protected function setUp(): void
    {
        parent::setUp();

        $this->fakeRazorpay('order_PAY1');
        $this->user = User::factory()->create();
        $this->order = $this->placeOrder($this->user, [[Product::factory()->create(['price' => 120000, 'stock' => 5]), 1]]);
    }

    public function test_valid_checkout_signature_marks_order_paid(): void
    {
        Event::fake([OrderPaid::class]);

        $this->verify('pay_1', hash_hmac('sha256', 'order_PAY1|pay_1', 'key-secret'))
            ->assertOk()
            ->assertJsonPath('data.status', 'paid');

        $this->assertDatabaseHas('payments', ['razorpay_payment_id' => 'pay_1', 'status' => 'captured', 'amount' => 120000]);
        Event::assertDispatchedTimes(OrderPaid::class, 1);
    }

    public function test_invalid_signature_is_rejected(): void
    {
        $this->verify('pay_1', 'forged-signature')->assertUnprocessable();

        $this->assertSame(OrderStatus::PendingPayment, $this->order->fresh()->status);
    }

    public function test_webhook_marks_order_paid(): void
    {
        Event::fake([OrderPaid::class]);

        $this->webhook('evt_1', 'payment.captured', 'pay_2', 120000)->assertOk();

        $this->assertSame(OrderStatus::Paid, $this->order->fresh()->status);
        Event::assertDispatchedTimes(OrderPaid::class, 1);
    }

    public function test_duplicate_webhook_delivery_is_processed_once(): void
    {
        Event::fake([OrderPaid::class]);

        $this->webhook('evt_1', 'payment.captured', 'pay_2', 120000)->assertJsonPath('status', 'ok');
        $this->webhook('evt_1', 'payment.captured', 'pay_2', 120000)->assertJsonPath('status', 'duplicate');

        $this->assertDatabaseCount('payments', 1);
        Event::assertDispatchedTimes(OrderPaid::class, 1);
    }

    public function test_checkout_callback_and_webhook_for_same_payment_pay_once(): void
    {
        Event::fake([OrderPaid::class]);

        $this->verify('pay_3', hash_hmac('sha256', 'order_PAY1|pay_3', 'key-secret'))->assertOk();
        $this->webhook('evt_9', 'payment.captured', 'pay_3', 120000)->assertOk();

        $this->assertDatabaseCount('payments', 1);
        Event::assertDispatchedTimes(OrderPaid::class, 1);
    }

    public function test_webhook_with_bad_signature_is_rejected(): void
    {
        $body = json_encode(['event' => 'payment.captured']);

        $this->call('POST', '/api/webhooks/razorpay', [], [], [], [
            'CONTENT_TYPE' => 'application/json',
            'HTTP_X_RAZORPAY_SIGNATURE' => 'nope',
        ], $body)->assertStatus(400);
    }

    public function test_amount_mismatch_does_not_mark_order_paid(): void
    {
        $this->webhook('evt_2', 'payment.captured', 'pay_4', 100)->assertOk();

        $this->assertSame(OrderStatus::PendingPayment, $this->order->fresh()->status);
    }

    public function test_failed_payment_is_recorded_and_order_stays_payable(): void
    {
        $this->webhook('evt_3', 'payment.failed', 'pay_5', 120000, 'Card declined')->assertOk();

        $this->assertDatabaseHas('payments', ['razorpay_payment_id' => 'pay_5', 'status' => 'failed', 'error_description' => 'Card declined']);
        $this->assertSame(OrderStatus::PendingPayment, $this->order->fresh()->status);
    }

    public function test_late_failure_event_does_not_downgrade_captured_payment(): void
    {
        $this->webhook('evt_4', 'payment.captured', 'pay_6', 120000);
        $this->webhook('evt_5', 'payment.failed', 'pay_6', 120000, 'late');

        $this->assertDatabaseHas('payments', ['razorpay_payment_id' => 'pay_6', 'status' => 'captured']);
    }

    private function verify(string $paymentId, string $signature)
    {
        return $this->withToken($this->jwtFor($this->user))->postJson(
            "/api/v1/orders/{$this->order->number}/verify-payment",
            ['razorpay_payment_id' => $paymentId, 'razorpay_signature' => $signature],
        );
    }

    private function webhook(string $eventId, string $type, string $paymentId, int $amount, ?string $error = null)
    {
        $body = json_encode([
            'event' => $type,
            'payload' => ['payment' => ['entity' => [
                'id' => $paymentId,
                'order_id' => 'order_PAY1',
                'amount' => $amount,
                'method' => 'upi',
                'error_description' => $error,
            ]]],
        ]);

        return $this->call('POST', '/api/webhooks/razorpay', [], [], [], [
            'CONTENT_TYPE' => 'application/json',
            'HTTP_ACCEPT' => 'application/json',
            'HTTP_X_RAZORPAY_EVENT_ID' => $eventId,
            'HTTP_X_RAZORPAY_SIGNATURE' => hash_hmac('sha256', $body, 'webhook-secret'),
        ], $body);
    }
}
