<?php

namespace App\Http\Resources;

use App\Models\Product;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Product */
class ProductResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'sku' => $this->sku,
            'name' => $this->name,
            'slug' => $this->slug,
            'description' => $this->description,
            'brand' => $this->brand,
            'price' => $this->price,
            'mrp' => $this->mrp,
            'currency' => 'INR',
            'in_stock' => $this->stock > 0,
            'stock' => $this->stock,
            'is_active' => $this->is_active,
            'attributes' => $this->attributes ?? (object) [],
            'category' => new CategoryResource($this->whenLoaded('category')),
        ];
    }
}
