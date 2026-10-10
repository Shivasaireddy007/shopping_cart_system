<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\SearchRequest;
use App\Http\Resources\ProductResource;
use App\Models\Product;
use App\Services\Catalog\ProductQuery;
use App\Services\Search\ProductSearch;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;

#[Group('Search', weight: 3)]
class SearchController extends Controller
{
    /**
     * Full-text product search with facets.
     *
     * Runs on Elasticsearch: each facet's counts ignore its own selection, so other options
     * stay visible. If Elasticsearch is unavailable, falls back to database filtering and
     * returns `facets: null` with `meta.engine = "database"`.
     */
    public function __invoke(SearchRequest $request, ProductSearch $search, ProductQuery $fallback): JsonResponse
    {
        $params = $request->validated();
        $page = $params['page'] ?? 1;
        $perPage = $params['per_page'] ?? 24;

        if (config('services.elasticsearch.enabled')) {
            try {
                $result = $search->search($params);

                $products = Product::with('category')->findMany($result->ids)
                    ->sortBy(fn (Product $product) => array_search($product->id, $result->ids))
                    ->values();

                return response()->json([
                    'data' => ProductResource::collection($products),
                    'facets' => $result->facets,
                    'meta' => ['total' => $result->total, 'page' => $page, 'per_page' => $perPage, 'engine' => 'elasticsearch'],
                ]);
            } catch (ConnectionException|RequestException $e) {
                Log::warning('Search falling back to database', ['error' => $e->getMessage()]);
            }
        }

        // Degraded mode: plain database filtering, no full-text relevance or facets.
        $paginator = $fallback->paginate([
            'brand' => $params['brand'][0] ?? null,
            'category' => $params['category'][0] ?? null,
            'min_price' => $params['min_price'] ?? null,
            'max_price' => $params['max_price'] ?? null,
            'in_stock' => $params['in_stock'] ?? false,
            'sort' => in_array($params['sort'] ?? null, ['price_asc', 'price_desc'], true) ? $params['sort'] : 'newest',
            'page' => $page,
            'per_page' => $perPage,
        ]);

        return response()->json([
            'data' => ProductResource::collection($paginator->items()),
            'facets' => null,
            'meta' => ['total' => $paginator->total(), 'page' => $page, 'per_page' => $perPage, 'engine' => 'database'],
        ]);
    }
}
