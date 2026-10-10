<?php

namespace App\Models;

use App\Services\Cart\ShippingFee;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Cart extends Model
{
    protected $fillable = ['user_id'];

    /** @return BelongsTo<User, $this> */
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    /** @return HasMany<CartItem, $this> */
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
        return ShippingFee::for($this->subtotal());
    }

    public function total(): int
    {
        return $this->subtotal() + $this->shippingFee();
    }
}
