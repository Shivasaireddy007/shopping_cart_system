<?php

namespace App\Services\Cart;

class ShippingFee
{
    /**
     * Shipping fee in paise for an order subtotal in paise.
     */
    public static function for(int $subtotal): int
    {
        if ($subtotal === 0 || $subtotal >= config('commerce.shipping.free_above')) {
            return 0;
        }

        return config('commerce.shipping.flat_fee');
    }
}
