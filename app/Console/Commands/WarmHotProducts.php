<?php

namespace App\Console\Commands;

use App\Http\Resources\ProductResource;
use App\Models\Product;
use App\Services\Catalog\CatalogCache;
use App\Services\Catalog\HotProducts;
use Illuminate\Console\Command;

class WarmHotProducts extends Command
{
    protected $signature = 'catalog:warm-hot';

    protected $description = 'Pre-cache the most viewed products so they are always served from Redis';

    public function handle(HotProducts $hot, CatalogCache $cache): int
    {
        $ids = $hot->top(config('commerce.catalog_cache.hot_count'), config('commerce.catalog_cache.hot_window_hours'));

        $products = Product::active()->with('category')->whereIn('id', $ids)->get();

        foreach ($products as $product) {
            $cache->putProduct($product->slug, (new ProductResource($product))->response()->getData(true));
        }

        $cache->setHot($products->pluck('slug')->all());

        $this->info("Warmed {$products->count()} hot product(s).");

        return self::SUCCESS;
    }
}
