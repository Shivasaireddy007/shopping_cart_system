<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\CheckoutRequest;
use App\Http\Resources\OrderResource;
use App\Services\Orders\CheckoutService;
use App\Services\Payments\RazorpayClient;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;

#[Group('Checkout and orders', weight: 5)]
class CheckoutController extends Controller
{
    /**
     * Place an order from the cart.
     *
     * Reserves stock with locked product rows, creates a Razorpay order and returns the
     * details needed to open Razorpay Checkout. Returns `409` if stock ran out and `502` if
     * Razorpay is unavailable (the order is cancelled and the cart kept).
     */
    public function store(CheckoutRequest $request, CheckoutService $checkout, RazorpayClient $razorpay): JsonResponse
    {
        $order = $checkout->checkout($request->user(), $request->validated('shipping_address'));

        return response()->json([
            'data' => new OrderResource($order),
            // Everything the frontend needs to open Razorpay Checkout.
            'razorpay' => [
                'key_id' => $razorpay->keyId(),
                'order_id' => $order->razorpay_order_id,
                'amount' => $order->total,
                'currency' => $order->currency,
            ],
        ], 201);
    }
}
