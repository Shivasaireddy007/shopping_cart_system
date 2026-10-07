<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\CartResource;
use App\Models\CartItem;
use App\Models\Product;
use App\Services\Cart\CartService;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class CartController extends Controller
{
    public function __construct(private readonly CartService $carts)
    {
    }

    public function show(Request $request): CartResource
    {
        return new CartResource($this->carts->for($request->user()));
    }

    public function store(Request $request): CartResource
    {
        $data = $request->validate([
            'product_id' => ['required', 'integer', 'exists:products,id'],
            'quantity' => ['required', 'integer', 'min:1'],
        ]);

        $product = Product::active()->findOrFail($data['product_id']);

        return new CartResource($this->carts->add($request->user(), $product, $data['quantity']));
    }

    public function update(Request $request, CartItem $item): CartResource
    {
        $this->authorizeItem($request, $item);

        $data = $request->validate(['quantity' => ['required', 'integer', 'min:1']]);

        return new CartResource($this->carts->update($item, $data['quantity']));
    }

    public function destroy(Request $request, CartItem $item): CartResource
    {
        $this->authorizeItem($request, $item);

        return new CartResource($this->carts->remove($item));
    }

    public function clear(Request $request): Response
    {
        $this->carts->clear($this->carts->for($request->user()));

        return response()->noContent();
    }

    private function authorizeItem(Request $request, CartItem $item): void
    {
        abort_unless($item->cart->user_id === $request->user()->id, 404);
    }
}
