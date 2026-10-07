<?php

namespace App\Observers;

use App\Jobs\SyncProductToSearch;
use App\Models\Product;

class ProductObserver
{
    public function created(Product $product): void
    {
        $this->sync($product);
    }

    /**
     * Also covers $product->decrement('stock'), which fires "updated" but not "saved".
     */
    public function updated(Product $product): void
    {
        $this->sync($product);
    }

    public function deleted(Product $product): void
    {
        $this->sync($product);
    }

    private function sync(Product $product): void
    {
        if (config('services.elasticsearch.enabled')) {
            SyncProductToSearch::dispatch($product->id);
        }
    }
}
