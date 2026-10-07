<?php

namespace App\Listeners;

use App\Events\OrderPaid;
use App\Jobs\CreateShipment;

class CreateShipmentForPaidOrder
{
    public function handle(OrderPaid $event): void
    {
        CreateShipment::dispatch($event->order);
    }
}
