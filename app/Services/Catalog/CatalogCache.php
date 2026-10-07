<?php

namespace App\Services\Catalog;

use App\Models\Product;
use Closure;
use Illuminate\Support\Facades\Cache;

/**
 * Read-through cache for catalog pages.
 *
 * Listing keys embed a catalog version. Any product change bumps the
 * version, which retires every cached listing at once without scanning or
 * deleting keys; old entries simply expire. Product details are cached per
 * slug and forgotten individually.
 */
class CatalogCache
{
    private const VERSION_KEY = 'catalog:version';

    private const HOT_KEY = 'catalog:hot';

    /**
     * @param  Closure(): array  $build
     */
    public function listing(array $filters, Closure $build): array
    {
        if (! $this->enabled()) {
            return $build();
        }

        ksort($filters);
        $key = 'catalog:list:v'.$this->version().':'.md5(json_encode($filters));

        return Cache::remember($key, config('commerce.catalog_cache.listing_ttl'), $build);
    }

    /**
     * @param  Closure(): array  $build
     */
    public function product(string $slug, Closure $build): array
    {
        if (! $this->enabled()) {
            return $build();
        }

        $ttl = $this->isHot($slug) ? config('commerce.catalog_cache.hot_ttl') : config('commerce.catalog_cache.product_ttl');

        return Cache::remember($this->productKey($slug), $ttl, $build);
    }

    public function putProduct(string $slug, array $payload): void
    {
        Cache::put($this->productKey($slug), $payload, config('commerce.catalog_cache.hot_ttl'));
    }

    /**
     * @param  array<int, string>  $slugs
     */
    public function setHot(array $slugs): void
    {
        Cache::forever(self::HOT_KEY, array_fill_keys($slugs, true));
    }

    public function isHot(string $slug): bool
    {
        return isset(Cache::get(self::HOT_KEY, [])[$slug]);
    }

    public function invalidate(Product $product): void
    {
        Cache::forget($this->productKey($product->slug));

        if ($product->wasChanged('slug')) {
            Cache::forget($this->productKey($product->getOriginal('slug')));
        }

        if (Cache::add(self::VERSION_KEY, 2)) {
            return;
        }

        Cache::increment(self::VERSION_KEY);
    }

    private function version(): int
    {
        return (int) Cache::get(self::VERSION_KEY, 1);
    }

    private function productKey(string $slug): string
    {
        return 'catalog:product:'.$slug;
    }

    private function enabled(): bool
    {
        return (bool) config('commerce.catalog_cache.enabled');
    }
}
