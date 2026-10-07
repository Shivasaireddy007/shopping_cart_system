<?php

namespace App\Console\Commands;

use App\Services\Search\ProductIndex;
use Illuminate\Console\Command;

class ReindexProducts extends Command
{
    protected $signature = 'search:reindex {--chunk=1000 : Products per bulk request}';

    protected $description = 'Rebuild the product search index and swap it in without downtime';

    public function handle(ProductIndex $index): int
    {
        $started = microtime(true);
        $count = $index->rebuild((int) $this->option('chunk'));

        $this->info(sprintf('Indexed %d products into "%s" in %.1fs.', $count, $index->alias(), microtime(true) - $started));

        return self::SUCCESS;
    }
}
