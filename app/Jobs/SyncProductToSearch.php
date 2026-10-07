<?php

namespace App\Jobs;

use App\Models\Product;
use App\Services\Search\ProductIndex;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;

class SyncProductToSearch implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable;

    public int $tries = 3;

    public int $backoff = 30;

    public function __construct(public readonly int $productId)
    {
        $this->afterCommit();
    }

    public function handle(ProductIndex $index): void
    {
        $product = Product::with('category')->find($this->productId);

        $product === null ? $index->remove($this->productId) : $index->sync($product);
    }
}
