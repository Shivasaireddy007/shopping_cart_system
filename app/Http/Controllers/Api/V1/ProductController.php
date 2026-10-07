<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\ProductIndexRequest;
use App\Http\Resources\ProductResource;
use App\Models\Product;
use App\Services\Catalog\CatalogCache;
use App\Services\Catalog\HotProducts;
use App\Services\Catalog\ProductQuery;
use Illuminate\Http\JsonResponse;

class ProductController extends Controller
{
    public function __construct(private readonly CatalogCache $cache)
    {
    }

    public function index(ProductIndexRequest $request, ProductQuery $query): JsonResponse
    {
        $filters = $request->validated();

        $payload = $this->cache->listing($filters, fn () => ProductResource::collection($query->paginate($filters))
            ->response()
            ->getData(true));

        return response()->json($payload);
    }

    public function show(string $slug, HotProducts $hot): JsonResponse
    {
        $payload = $this->cache->product($slug, fn () => (new ProductResource(
            Product::active()->with('category')->where('slug', $slug)->firstOrFail()
        ))->response()->getData(true));

        $hot->recordView($payload['data']['id']);

        return response()->json($payload);
    }
}
