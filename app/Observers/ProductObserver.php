<?php

namespace App\Observers;

use App\Jobs\SyncProductToSearch;
use App\Models\Product;
use App\Services\Catalog\CatalogCache;
use Illuminate\Support\Facades\DB;

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
        // Runs once the surrounding transaction (e.g. checkout) has committed.
        DB::afterCommit(fn () => app(CatalogCache::class)->invalidate($product));

        if (config('services.elasticsearch.enabled')) {
            SyncProductToSearch::dispatch($product->id);
        }
    }
}
