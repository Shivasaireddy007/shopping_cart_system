<?php

namespace App\Console\Commands;

use App\Enums\OrderStatus;
use App\Models\Order;
use App\Services\Orders\OrderCanceller;
use Illuminate\Console\Command;

class ExpireUnpaidOrders extends Command
{
    protected $signature = 'orders:expire-unpaid {--minutes=30 : Cancel orders left unpaid for longer than this}';

    protected $description = 'Cancel orders that were never paid and release their reserved stock';

    public function handle(OrderCanceller $canceller): int
    {
        $cutoff = now()->subMinutes((int) $this->option('minutes'));
        $cancelled = 0;

        Order::where('status', OrderStatus::PendingPayment)
            ->where('created_at', '<', $cutoff)
            ->eachById(function (Order $order) use ($canceller, &$cancelled) {
                $cancelled += (int) $canceller->cancel($order);
            });

        $this->info("Cancelled {$cancelled} unpaid order(s).");

        return self::SUCCESS;
    }
}
