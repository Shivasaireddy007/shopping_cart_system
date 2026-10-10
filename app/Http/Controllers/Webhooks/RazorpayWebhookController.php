<?php

namespace App\Http\Controllers\Webhooks;

use App\Http\Controllers\Controller;
use App\Models\WebhookEvent;
use App\Services\Payments\PaymentRecorder;
use App\Services\Payments\RazorpayClient;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

#[Group('Webhooks', weight: 7)]
class RazorpayWebhookController extends Controller
{
    /**
     * Receive Razorpay payment events.
     *
     * Verified with the `X-Razorpay-Signature` HMAC of the raw body. Each event id is
     * processed once; repeats return `{"status": "duplicate"}`.
     */
    public function __invoke(Request $request, RazorpayClient $razorpay, PaymentRecorder $payments): JsonResponse
    {
        $payload = $request->getContent();

        if (! $razorpay->isValidWebhookSignature($payload, (string) $request->header('X-Razorpay-Signature'))) {
            return response()->json(['message' => 'Invalid signature.'], 400);
        }

        $event = json_decode($payload, true) ?? [];
        $eventId = $request->header('X-Razorpay-Event-Id') ?: hash('sha256', $payload);

        // Razorpay delivers at least once; the unique key makes us process each event once.
        $isNew = WebhookEvent::insertOrIgnore([
            'provider' => 'razorpay',
            'event_id' => $eventId,
            'type' => $event['event'] ?? 'unknown',
            'created_at' => now(),
            'updated_at' => now(),
        ]) === 1;

        if (! $isNew) {
            return response()->json(['status' => 'duplicate']);
        }

        try {
            $this->handle($event, $payments);
        } catch (Throwable $e) {
            // Forget the event so Razorpay's retry gets processed.
            WebhookEvent::where(['provider' => 'razorpay', 'event_id' => $eventId])->delete();

            throw $e;
        }

        WebhookEvent::where(['provider' => 'razorpay', 'event_id' => $eventId])->update(['processed_at' => now()]);

        return response()->json(['status' => 'ok']);
    }

    private function handle(array $event, PaymentRecorder $payments): void
    {
        $payment = $event['payload']['payment']['entity'] ?? null;

        if ($payment === null || empty($payment['order_id'])) {
            return;
        }

        match ($event['event'] ?? null) {
            'payment.captured', 'order.paid' => $payments->captured($payment['order_id'], $payment['id'], (int) $payment['amount'], $payment['method'] ?? null),
            'payment.failed' => $payments->failed($payment['order_id'], $payment['id'], (int) $payment['amount'], $payment['error_description'] ?? null),
            default => null,
        };
    }
}
