<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\ProductIndexRequest;
use App\Http\Resources\ProductResource;
use App\Models\Product;
use App\Services\Catalog\ProductQuery;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class ProductController extends Controller
{
    public function index(ProductIndexRequest $request, ProductQuery $query): AnonymousResourceCollection
    {
        return ProductResource::collection($query->paginate($request->validated()));
    }

    public function show(string $slug): ProductResource
    {
        $product = Product::active()->with('category')->where('slug', $slug)->firstOrFail();

        return new ProductResource($product);
    }
}
