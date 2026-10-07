<?php

namespace App\Http\Resources;

use App\Models\CartItem;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Cart */
class CartResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'items' => $this->items->map(fn (CartItem $item) => [
                'id' => $item->id,
                'product_id' => $item->product_id,
                'sku' => $item->product->sku,
                'name' => $item->product->name,
                'unit_price' => $item->product->price,
                'quantity' => $item->quantity,
                'line_total' => $item->lineTotal(),
            ])->values(),
            'subtotal' => $this->subtotal(),
            'shipping_fee' => $this->shippingFee(),
            'total' => $this->total(),
            'currency' => 'INR',
        ];
    }

    /**
     * The cart is created lazily on first access, which would otherwise make
     * Laravel answer 201 Created for a plain read or item update.
     */
    public function withResponse(Request $request, JsonResponse $response): void
    {
        $response->setStatusCode(200);
    }
}
