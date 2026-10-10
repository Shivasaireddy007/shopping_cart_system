<?php

namespace App\Listeners;

use App\Events\OrderPaid;
use App\Jobs\CreateShipment;
use Illuminate\Support\Facades\Log;

class CreateShipmentForPaidOrder
{
    public function handle(OrderPaid $event): void
    {
        // Without Shiprocket credentials (e.g. the public demo), orders stay "paid" and nothing ships.
        if (blank(config('services.shiprocket.email')) || blank(config('services.shiprocket.password'))) {
            Log::info('Shiprocket not configured, skipping shipment', ['order' => $event->order->number]);

            return;
        }

        CreateShipment::dispatch($event->order);
    }
}
