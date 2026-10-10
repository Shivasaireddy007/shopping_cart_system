<?php

namespace App\Models;

use App\Enums\OrderStatus;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;
use Illuminate\Support\Str;

class Order extends Model
{
    protected $fillable = [
        'number', 'user_id', 'status', 'subtotal', 'shipping_fee', 'total',
        'currency', 'shipping_address', 'razorpay_order_id', 'paid_at', 'cancelled_at',
    ];

    protected $casts = [
        'status' => OrderStatus::class,
        'subtotal' => 'integer',
        'shipping_fee' => 'integer',
        'total' => 'integer',
        'shipping_address' => 'array',
        'paid_at' => 'datetime',
        'cancelled_at' => 'datetime',
    ];

    protected static function booted(): void
    {
        static::creating(function (Order $order) {
            $order->number ??= 'ORD-'.now()->format('Ymd').'-'.Str::upper(Str::random(6));
        });
    }

    public function getRouteKeyName(): string
    {
        return 'number';
    }

    /** @return BelongsTo<User, $this> */
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    /** @return HasMany<OrderItem, $this> */
    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }

    /** @return HasMany<Payment, $this> */
    public function payments(): HasMany
    {
        return $this->hasMany(Payment::class);
    }

    /** @return HasOne<Shipment, $this> */
    public function shipment(): HasOne
    {
        return $this->hasOne(Shipment::class);
    }

    public function isPaid(): bool
    {
        return $this->paid_at !== null;
    }

    public function totalWeightGrams(): int
    {
        return $this->items->sum(fn (OrderItem $item) => $item->weight_grams * $item->quantity);
    }
}
