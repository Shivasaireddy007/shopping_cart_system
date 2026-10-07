<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Cart extends Model
{
    protected $fillable = ['user_id'];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function items(): HasMany
    {
        return $this->hasMany(CartItem::class);
    }

    /**
     * Subtotal in paise, priced at the current product prices.
     */
    public function subtotal(): int
    {
        return $this->items->sum(fn (CartItem $item) => $item->lineTotal());
    }

    public function shippingFee(): int
    {
        $subtotal = $this->subtotal();

        if ($subtotal === 0 || $subtotal >= config('commerce.shipping.free_above')) {
            return 0;
        }

        return config('commerce.shipping.flat_fee');
    }

    public function total(): int
    {
        return $this->subtotal() + $this->shippingFee();
    }
}
