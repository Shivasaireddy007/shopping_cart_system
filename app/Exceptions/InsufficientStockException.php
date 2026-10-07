<?php

namespace App\Exceptions;

use App\Models\Product;
use Illuminate\Http\JsonResponse;
use RuntimeException;

class InsufficientStockException extends RuntimeException
{
    public function __construct(public readonly Product $product, public readonly int $requested)
    {
        parent::__construct("Only {$product->stock} unit(s) of {$product->sku} available, {$requested} requested.");
    }

    public function render(): JsonResponse
    {
        return response()->json([
            'message' => $this->getMessage(),
            'sku' => $this->product->sku,
            'available' => $this->product->stock,
        ], 409);
    }
}
