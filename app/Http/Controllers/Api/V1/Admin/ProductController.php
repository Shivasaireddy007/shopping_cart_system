<?php

namespace App\Http\Controllers\Api\V1\Admin;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\Admin\ProductRequest;
use App\Http\Resources\ProductResource;
use App\Models\Product;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

#[Group('Admin', weight: 6)]
class ProductController extends Controller
{
    /**
     * Lists all products, including inactive ones, optionally searched by SKU or name.
     */
    public function index(Request $request): AnonymousResourceCollection
    {
        $search = $request->string('search')->trim()->value();

        $products = Product::with('category')
            ->when($search !== '', fn ($q) => $q->where(fn ($q) => $q
                ->where('sku', $search)
                ->orWhere('name', 'like', '%'.addcslashes($search, '%_').'%')))
            ->latest('id')
            ->paginate(50);

        return ProductResource::collection($products);
    }

    /**
     * Create a product. The slug is generated from the name if not given.
     */
    public function store(ProductRequest $request): JsonResponse
    {
        $product = Product::create($request->validated());

        return (new ProductResource($product->load('category')))->response()->setStatusCode(201);
    }

    /**
     * Update a product, e.g. its price or stock.
     */
    public function update(ProductRequest $request, Product $product): ProductResource
    {
        $product->update($request->validated());

        return new ProductResource($product->load('category'));
    }

    /**
     * Archives the product instead of deleting it, so past orders keep their link to it.
     */
    public function destroy(Product $product): ProductResource
    {
        $product->update(['is_active' => false]);

        return new ProductResource($product->load('category'));
    }
}
