<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Product extends Model
{
    use HasFactory;

    protected $fillable = [
        'category_id', 'sku', 'name', 'slug', 'description', 'brand',
        'price', 'mrp', 'stock', 'weight_grams', 'attributes', 'is_active',
    ];

    protected $casts = [
        'price' => 'integer',
        'mrp' => 'integer',
        'stock' => 'integer',
        'weight_grams' => 'integer',
        'attributes' => 'array',
        'is_active' => 'boolean',
    ];

    public function category(): BelongsTo
    {
        return $this->belongsTo(Category::class);
    }

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('is_active', true);
    }

    public function isInStock(int $quantity = 1): bool
    {
        return $this->is_active && $this->stock >= $quantity;
    }
}
