<?php

namespace App\Services\Cart;

use App\Exceptions\InsufficientStockException;
use App\Models\Cart;
use App\Models\CartItem;
use App\Models\Product;
use App\Models\User;

class CartService
{
    public function for(User $user): Cart
    {
        return Cart::firstOrCreate(['user_id' => $user->id])->load('items.product');
    }

    /**
     * Adds a product to the cart, increasing the quantity if it is already there.
     */
    public function add(User $user, Product $product, int $quantity): Cart
    {
        $cart = $this->for($user);
        $current = (int) $cart->items->where('product_id', $product->id)->sum('quantity');

        $this->setQuantity($cart, $product, $current + $quantity);

        return $cart->load('items.product');
    }

    public function update(CartItem $item, int $quantity): Cart
    {
        $this->setQuantity($item->cart, $item->product, $quantity);

        return $item->cart->load('items.product');
    }

    public function remove(CartItem $item): Cart
    {
        $cart = $item->cart;
        $item->delete();

        return $cart->load('items.product');
    }

    public function clear(Cart $cart): void
    {
        $cart->items()->delete();
    }

    private function setQuantity(Cart $cart, Product $product, int $quantity): void
    {
        $quantity = min($quantity, config('commerce.cart.max_quantity_per_item'));

        if (! $product->isInStock($quantity)) {
            throw new InsufficientStockException($product, $quantity);
        }

        $cart->items()->updateOrCreate(['product_id' => $product->id], ['quantity' => $quantity]);
    }
}
