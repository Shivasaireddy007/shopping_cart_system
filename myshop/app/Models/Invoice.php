<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str; // Import Str helper

class Invoice extends Model
{
    use HasFactory;

    protected $table = 'invoices'; // Ensure it matches your database table

    protected $fillable = ['invoiceno', 'amount', 'customer_id', 'status']; // Add actual column names

    // Automatically generate 'invoiceno' if not provided
    protected static function boot()
    {
        parent::boot();
        static::creating(function ($invoice) {
            if (empty($invoice->invoiceno)) {
                // Generate unique invoice number (e.g., INV-6543A12)
                $invoice->invoiceno = 'INV-' . Str::upper(Str::random(6));
            }
        });
    }
}
