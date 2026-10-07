<?php

namespace App\Services\Catalog;

use App\Models\Product;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;

/**
 * Filters, sorts and paginates the active product catalog.
 */
class ProductQuery
{
    public const SORTS = [
        'newest' => ['id', 'desc'],
        'price_asc' => ['price', 'asc'],
        'price_desc' => ['price', 'desc'],
        'name' => ['name', 'asc'],
    ];

    /**
     * @param  array{category?: string, brand?: string, min_price?: int, max_price?: int, in_stock?: bool, sort?: string, per_page?: int, page?: int}  $filters
     */
    public function paginate(array $filters): LengthAwarePaginator
    {
        [$column, $direction] = self::SORTS[$filters['sort'] ?? 'newest'];

        return Product::query()
            ->active()
            ->with('category')
            ->when($filters['category'] ?? null, fn ($q, $slug) => $q->whereHas('category', fn ($c) => $c->where('slug', $slug)))
            ->when($filters['brand'] ?? null, fn ($q, $brand) => $q->where('brand', $brand))
            ->when(isset($filters['min_price']), fn ($q) => $q->where('price', '>=', $filters['min_price']))
            ->when(isset($filters['max_price']), fn ($q) => $q->where('price', '<=', $filters['max_price']))
            ->when($filters['in_stock'] ?? false, fn ($q) => $q->where('stock', '>', 0))
            ->orderBy($column, $direction)
            ->orderBy('id', 'desc')
            ->paginate($filters['per_page'] ?? 24, ['*'], 'page', $filters['page'] ?? 1);
    }
}
