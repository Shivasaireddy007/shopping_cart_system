<?php

namespace App\Services\Catalog;

use Illuminate\Redis\Connections\Connection;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;
use Throwable;

/**
 * Tracks product views in hourly Redis sorted sets and returns the most
 * viewed products over a sliding window.
 */
class HotProducts
{
    private const PREFIX = 'catalog:views:';

    public function recordView(int $productId): void
    {
        $key = self::PREFIX.now()->format('YmdH');

        try {
            // @phpstan-ignore arguments.count (Laravel's Redis connection proxies pipeline() with a callback)
            $this->redis()->pipeline(function ($pipe) use ($key, $productId) {
                $pipe->zincrby($key, 1, (string) $productId);
                $pipe->expire($key, 26 * 3600);
            });
        } catch (Throwable $e) {
            // View counting must never break a product page.
            Log::warning('Could not record product view', ['error' => $e->getMessage()]);
        }
    }

    /**
     * @return array<int, int> Product ids, most viewed first
     */
    public function top(int $limit, int $hours = 24): array
    {
        $keys = [];
        for ($i = 0; $i < $hours; $i++) {
            $keys[] = self::PREFIX.now()->subHours($i)->format('YmdH');
        }

        $destination = self::PREFIX.'window:'.now()->format('YmdHis').':'.random_int(1000, 9999);

        $this->redis()->zunionstore($destination, $keys);
        $ids = $this->redis()->zrevrange($destination, 0, $limit - 1);
        $this->redis()->del($destination);

        return array_map('intval', $ids);
    }

    private function redis(): Connection
    {
        return Redis::connection('cache');
    }
}
