<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Invoice extends Model
{
    use HasFactory;

    protected $fillable = ['invoiceno', 'amount', 'customer_id', 'status'];

    protected $casts = [
        'amount' => 'decimal:2',
        'customer_id' => 'integer',
    ];

    /**
     * Generate an invoice number (e.g. INV-6543A1) when none is given.
     */
    protected static function booted(): void
    {
        static::creating(function (Invoice $invoice) {
            if (empty($invoice->invoiceno)) {
                $invoice->invoiceno = 'INV-' . Str::upper(Str::random(6));
            }
        });
    }
}
