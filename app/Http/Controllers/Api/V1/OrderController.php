<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\OrderResource;
use App\Models\Order;
use App\Services\Orders\OrderCanceller;
use App\Services\Payments\PaymentRecorder;
use App\Services\Payments\RazorpayClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class OrderController extends Controller
{
    public function index(Request $request): AnonymousResourceCollection
    {
        return OrderResource::collection($request->user()->orders()->latest('id')->paginate(10));
    }

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
