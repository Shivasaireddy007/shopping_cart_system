<?php

namespace App\Services\Orders;

use App\Enums\OrderStatus;
use App\Models\Order;
use App\Models\Product;
use Illuminate\Support\Facades\DB;

class OrderCanceller
{
    /**
     * Cancels an unpaid order and puts its stock back. Returns false when the
     * order is no longer pending payment (e.g. it was paid in the meantime).
     */
    public function cancel(Order $order): bool
    {
        return DB::transaction(function () use ($order) {
            $order = Order::whereKey($order->id)->lockForUpdate()->with('items')->firstOrFail();

            if ($order->status !== OrderStatus::PendingPayment) {
                return false;
            }

            $quantities = $order->items->whereNotNull('product_id')->groupBy('product_id')
                ->map(fn ($items) => $items->sum('quantity'));

            Product::whereIn('id', $quantities->keys())->orderBy('id')->lockForUpdate()->get()
                ->each(fn (Product $product) => $product->increment('stock', $quantities[$product->id]));

            $order->update(['status' => OrderStatus::Cancelled, 'cancelled_at' => now()]);

            return true;
        });
    }
}
