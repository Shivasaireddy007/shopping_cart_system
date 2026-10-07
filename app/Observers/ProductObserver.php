<?php

namespace App\Observers;

use App\Jobs\SyncProductToSearch;
use App\Models\Product;

class ProductObserver
{
    public function saved(Product $product): void
    {
        if (config('services.elasticsearch.enabled')) {
            SyncProductToSearch::dispatch($product->id);
        }
    }

    public function deleted(Product $product): void
    {
        if (config('services.elasticsearch.enabled')) {
            SyncProductToSearch::dispatch($product->id);
        }
    }
}
