<?php

namespace App\Services\Payments;

use App\Enums\OrderStatus;
use App\Events\OrderPaid;
use App\Models\Order;
use App\Models\Payment;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

/**
 * Records Razorpay payments against orders. Both the checkout callback and
 * the webhook can report the same payment, so every method is idempotent.
 */
class PaymentRecorder
{
    public function captured(string $razorpayOrderId, string $paymentId, int $amount, ?string $method = null): ?Order
    {
        return DB::transaction(function () use ($razorpayOrderId, $paymentId, $amount, $method) {
            $order = Order::where('razorpay_order_id', $razorpayOrderId)->lockForUpdate()->first();

            if ($order === null) {
                Log::warning('Payment for unknown Razorpay order', ['razorpay_order_id' => $razorpayOrderId, 'payment' => $paymentId]);

                return null;
            }

            $this->record($order, $paymentId, $amount, 'captured', $method);

            if ($order->isPaid()) {
                return $order;
            }

            if ($amount !== $order->total) {
                Log::critical('Captured amount does not match order total', [
                    'order' => $order->number, 'expected' => $order->total, 'captured' => $amount,
                ]);

                return $order;
            }

            if ($order->status === OrderStatus::Cancelled) {
                Log::critical('Payment captured for a cancelled order, refund required', [
                    'order' => $order->number, 'payment' => $paymentId,
                ]);

                return $order;
            }

            $order->update(['status' => OrderStatus::Paid, 'paid_at' => now()]);

            OrderPaid::dispatch($order);

            return $order;
        });
    }

    public function failed(string $razorpayOrderId, string $paymentId, int $amount, ?string $error = null): void
    {
        $order = Order::where('razorpay_order_id', $razorpayOrderId)->first();

        if ($order !== null) {
            $this->record($order, $paymentId, $amount, 'failed', null, $error);
        }
    }

    private function record(Order $order, string $paymentId, int $amount, string $status, ?string $method, ?string $error = null): void
    {
        $payment = Payment::firstOrNew(['razorpay_payment_id' => $paymentId]);

        // Never downgrade a captured payment if a late "failed" event arrives.
        if ($payment->exists && $payment->status === 'captured') {
            return;
        }

        $payment->fill([
            'razorpay_order_id' => $order->razorpay_order_id,
            'amount' => $amount,
            'status' => $status,
            'method' => $method ?? $payment->method,
            'error_description' => $error,
        ]);
        $payment->order()->associate($order);
        $payment->save();
    }
}
