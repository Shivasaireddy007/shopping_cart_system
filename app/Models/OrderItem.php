<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class OrderItem extends Model
{
    protected $fillable = [
        'product_id', 'sku', 'name', 'unit_price', 'quantity', 'line_total', 'weight_grams',
    ];

    protected $casts = [
        'unit_price' => 'integer',
        'quantity' => 'integer',
        'line_total' => 'integer',
        'weight_grams' => 'integer',
    ];

    /** @return BelongsTo<Order, $this> */
    public function order(): BelongsTo
    {
        return $this->belongsTo(Order::class);
    }

    /** @return BelongsTo<Product, $this> */
    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }
}
