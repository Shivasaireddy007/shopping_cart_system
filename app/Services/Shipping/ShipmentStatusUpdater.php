<?php

namespace App\Services\Shipping;

use App\Enums\OrderStatus;
use App\Models\Shipment;
use Illuminate\Support\Facades\DB;

/**
 * Applies Shiprocket status updates. Webhooks can arrive out of order, so
 * an order only ever moves forward: paid -> shipped -> delivered.
 */
class ShipmentStatusUpdater
{
    private const SHIPPED = ['PICKED UP', 'SHIPPED', 'IN TRANSIT', 'OUT FOR DELIVERY', 'REACHED AT DESTINATION HUB'];

    private const DELIVERED = ['DELIVERED'];

    private const RANK = [
        OrderStatus::Paid->value => 1,
        OrderStatus::Shipped->value => 2,
        OrderStatus::Delivered->value => 3,
    ];

    public function apply(string $awb, string $courierStatus): ?Shipment
    {
        return DB::transaction(function () use ($awb, $courierStatus) {
            $shipment = Shipment::where('awb_code', $awb)->lockForUpdate()->with('order')->first();

            if ($shipment === null) {
                return null;
            }

            $courierStatus = strtoupper(trim($courierStatus));
            $target = $this->orderStatusFor($courierStatus);
            $order = $shipment->order;

            if ($target === null) {
                $shipment->update(['status' => strtolower($courierStatus), 'status_updated_at' => now()]);

                return $shipment;
            }

            if ((self::RANK[$target->value] ?? 0) > (self::RANK[$order->status->value] ?? 0)) {
                $shipment->update(['status' => strtolower($courierStatus), 'status_updated_at' => now()]);
                $order->update(['status' => $target]);
            }

            return $shipment;
        });
    }

    private function orderStatusFor(string $courierStatus): ?OrderStatus
    {
        return match (true) {
            in_array($courierStatus, self::DELIVERED, true) => OrderStatus::Delivered,
            in_array($courierStatus, self::SHIPPED, true) => OrderStatus::Shipped,
            default => null,
        };
    }
}
