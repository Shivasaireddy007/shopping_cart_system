<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Resources\CartResource;
use App\Models\CartItem;
use App\Models\Product;
use App\Services\Cart\CartService;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

#[Group('Cart', weight: 4)]
class CartController extends Controller
{
    public function __construct(private readonly CartService $carts) {}

    /**
     * Get the cart with live prices, shipping fee and total.
     */
    public function show(Request $request): CartResource
    {
        return new CartResource($this->carts->for($request->user()));
    }

    /**
     * Add a product, or increase its quantity if it is already in the cart.
     *
     * Returns `409` if there is not enough stock.
     */
    public function store(Request $request): CartResource
    {
        $data = $request->validate([
            'product_id' => ['required', 'integer', 'exists:products,id'],
            'quantity' => ['required', 'integer', 'min:1'],
        ]);

        $product = Product::active()->findOrFail($data['product_id']);

        return new CartResource($this->carts->add($request->user(), $product, $data['quantity']));
    }

    /**
     * Set the quantity of a cart item.
     */
    public function update(Request $request, CartItem $item): CartResource
    {
        $this->authorizeItem($request, $item);

        $data = $request->validate(['quantity' => ['required', 'integer', 'min:1']]);

        return new CartResource($this->carts->update($item, $data['quantity']));
    }

    /**
     * Remove an item from the cart.
     */
    public function destroy(Request $request, CartItem $item): CartResource
    {
        $this->authorizeItem($request, $item);

        return new CartResource($this->carts->remove($item));
    }

    /**
     * Empty the cart.
     */
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
