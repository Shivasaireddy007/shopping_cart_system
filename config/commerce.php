<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Shipping charges
    |--------------------------------------------------------------------------
    |
    | All amounts are in paise. Orders at or above the free shipping
    | threshold ship for free, everything else pays the flat fee.
    |
    */

    'shipping' => [
        'flat_fee' => (int) env('SHIPPING_FLAT_FEE', 4900),
        'free_above' => (int) env('SHIPPING_FREE_ABOVE', 99900),
    ],

    'cart' => [
        'max_quantity_per_item' => 10,
    ],

    /*
    |--------------------------------------------------------------------------
    | Catalog caching
    |--------------------------------------------------------------------------
    |
    | Listing pages and product details are cached in Redis. The most viewed
    | ("hot") products are pre-warmed on a schedule and kept for longer.
    | TTLs are in seconds.
    |
    */

    'catalog_cache' => [
        'enabled' => (bool) env('CATALOG_CACHE_ENABLED', true),
        'listing_ttl' => 300,
        'product_ttl' => 600,
        'hot_ttl' => 3600,
        'hot_count' => 100,
        'hot_window_hours' => 24,
    ],

];
