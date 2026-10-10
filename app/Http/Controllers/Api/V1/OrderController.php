<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\OrderResource;
use App\Models\Order;
use App\Services\Orders\OrderCanceller;
use App\Services\Payments\PaymentRecorder;
use App\Services\Payments\RazorpayClient;
use App\Services\Shipping\ShiprocketClient;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Support\Facades\Cache;

#[Group('Checkout and orders', weight: 5)]
class OrderController extends Controller
{
    /**
     * List your orders, newest first.
     */
    public function index(Request $request): AnonymousResourceCollection
    {
        return OrderResource::collection($request->user()->orders()->latest('id')->paginate(10));
    }

    /**
     * Get one of your orders by its number.
     */
    public function show(Request $request, Order $order): OrderResource
    {
        $this->authorizeOrder($request, $order);

        return new OrderResource($order->load('items'));
    }

    /**
     * Confirms a payment using the signature returned by Razorpay Checkout.
     */
    public function verifyPayment(Request $request, Order $order, RazorpayClient $razorpay, PaymentRecorder $payments): OrderResource|JsonResponse
    {
        $this->authorizeOrder($request, $order);

        $data = $request->validate([
            'razorpay_payment_id' => ['required', 'string', 'max:64'],
            'razorpay_signature' => ['required', 'string', 'max:128'],
        ]);

        if ($order->razorpay_order_id === null
            || ! $razorpay->isValidPaymentSignature($order->razorpay_order_id, $data['razorpay_payment_id'], $data['razorpay_signature'])) {
            return response()->json(['message' => 'Invalid payment signature.'], 422);
        }

        $order = $payments->captured($order->razorpay_order_id, $data['razorpay_payment_id'], $order->total);

        return new OrderResource($order->load('items'));
    }

    /**
     * Get courier details and the tracking timeline for an order.
     */
    public function tracking(Request $request, Order $order, ShiprocketClient $shiprocket): JsonResponse
    {
        $this->authorizeOrder($request, $order);

        $shipment = $order->shipment;

        if ($shipment === null || ! $shipment->hasAwb()) {
            return response()->json(['data' => ['status' => $order->status->value, 'awb_code' => null, 'events' => []]]);
        }

        $tracking = Cache::remember("tracking:{$shipment->awb_code}", now()->addMinutes(10), fn () => $shiprocket->track($shipment->awb_code));

        return response()->json(['data' => [
            'status' => $order->status->value,
            'awb_code' => $shipment->awb_code,
            'courier_name' => $shipment->courier_name,
            'events' => $tracking['shipment_track_activities'] ?? [],
            'track_url' => $tracking['track_url'] ?? null,
        ]]);
    }

    /**
     * Cancel an unpaid order and release its stock.
     *
     * Returns `409` once the order is paid.
     */
    public function cancel(Request $request, Order $order, OrderCanceller $canceller): OrderResource|JsonResponse
    {
        $this->authorizeOrder($request, $order);

        if (! $order->status->canBeCancelledByCustomer() || ! $canceller->cancel($order)) {
            return response()->json(['message' => 'This order can no longer be cancelled.'], 409);
        }

        return new OrderResource($order->refresh()->load('items'));
    }

    private function authorizeOrder(Request $request, Order $order): void
    {
        abort_unless($order->user_id === $request->user()->id, 404);
    }
}
