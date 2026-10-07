<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\CheckoutRequest;
use App\Http\Resources\OrderResource;
use App\Services\Orders\CheckoutService;
use App\Services\Payments\RazorpayClient;
use Illuminate\Http\JsonResponse;

class CheckoutController extends Controller
{
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
