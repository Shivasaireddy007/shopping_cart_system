<?php

namespace App\Services\Orders;

use App\Enums\OrderStatus;
use App\Exceptions\EmptyCartException;
use App\Exceptions\InsufficientStockException;
use App\Exceptions\PaymentGatewayException;
use App\Models\Cart;
use App\Models\Order;
use App\Models\Product;
use App\Models\User;
use App\Services\Cart\ShippingFee;
use App\Services\Payments\RazorpayClient;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Throwable;

class CheckoutService
{
    public function __construct(
        private readonly RazorpayClient $razorpay,
        private readonly OrderCanceller $canceller,
    ) {
    }

    /**
     * Turns the user's cart into an order and opens a Razorpay order for it.
     *
     * Stock is reserved inside a transaction with the product rows locked
     * (in id order, so concurrent checkouts cannot deadlock or oversell).
     * The Razorpay call happens after the commit; if it fails, the order is
     * cancelled, which releases the stock, and the cart is left untouched.
     *
     * @param  array<string, string>  $shippingAddress
     */
    public function checkout(User $user, array $shippingAddress): Order
    {
        $cart = Cart::where('user_id', $user->id)->with('items')->first();

        if ($cart === null || $cart->items->isEmpty()) {
            throw new EmptyCartException();
        }

        $order = DB::transaction(fn () => $this->reserve($user, $cart, $shippingAddress));

        try {
            $razorpayOrderId = $this->razorpay->createOrder($order->total, $order->number, [
                'order_number' => $order->number,
            ]);
        } catch (Throwable $e) {
            Log::error('Razorpay order creation failed', ['order' => $order->number, 'error' => $e->getMessage()]);
            $this->canceller->cancel($order);

            throw new PaymentGatewayException('Could not create Razorpay order.', previous: $e);
        }

        $order->update(['razorpay_order_id' => $razorpayOrderId]);
        $cart->items()->delete();

        return $order->load('items');
    }

    private function reserve(User $user, Cart $cart, array $shippingAddress): Order
    {
        $products = Product::whereIn('id', $cart->items->pluck('product_id'))
            ->orderBy('id')
            ->lockForUpdate()
            ->get()
            ->keyBy('id');

        $lines = [];

        foreach ($cart->items as $item) {
            $product = $products->get($item->product_id);

            if ($product === null || ! $product->isInStock($item->quantity)) {
                throw new InsufficientStockException($product ?? $item->product, $item->quantity);
            }

            $lines[] = [
                'product_id' => $product->id,
                'sku' => $product->sku,
                'name' => $product->name,
                'unit_price' => $product->price,
                'quantity' => $item->quantity,
                'line_total' => $product->price * $item->quantity,
                'weight_grams' => $product->weight_grams,
            ];

            $product->decrement('stock', $item->quantity);
        }

        $subtotal = array_sum(array_column($lines, 'line_total'));
        $shippingFee = ShippingFee::for($subtotal);

        $order = Order::create([
            'user_id' => $user->id,
            'status' => OrderStatus::PendingPayment,
            'subtotal' => $subtotal,
            'shipping_fee' => $shippingFee,
            'total' => $subtotal + $shippingFee,
            'shipping_address' => $shippingAddress,
        ]);

        $order->items()->createMany($lines);

        return $order;
    }
}
