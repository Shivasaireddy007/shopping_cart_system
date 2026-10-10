<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Shipment extends Model
{
    protected $fillable = [
        'shiprocket_order_id', 'shiprocket_shipment_id', 'awb_code', 'courier_name', 'status', 'status_updated_at',
    ];

    protected $casts = [
        'shiprocket_order_id' => 'integer',
        'shiprocket_shipment_id' => 'integer',
        'status_updated_at' => 'datetime',
    ];

    /** @return BelongsTo<Order, $this> */
    public function order(): BelongsTo
    {
        return $this->belongsTo(Order::class);
    }

    public function hasAwb(): bool
    {
        return $this->awb_code !== null;
    }
}
