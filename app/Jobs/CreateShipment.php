<?php

namespace App\Jobs;

use App\Models\Order;
use App\Services\Shipping\ShiprocketClient;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

/**
 * Creates the Shiprocket order and assigns a courier for a paid order.
 *
 * Each step is saved as soon as it succeeds, so a retry after a failure
 * (e.g. AWB assignment timing out) continues instead of creating a
 * duplicate Shiprocket order.
 */
class CreateShipment implements ShouldBeUnique, ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 5;

    public function __construct(public readonly Order $order) {}

    /**
     * @return array<int, int>
     */
    public function backoff(): array
    {
        return [60, 300, 900, 3600];
    }

    public function uniqueId(): string
    {
        return (string) $this->order->id;
    }

    public function handle(ShiprocketClient $shiprocket): void
    {
        $order = $this->order->load(['items', 'user', 'shipment']);
        $shipment = $order->shipment ?? $order->shipment()->make();

        if ($shipment->hasAwb()) {
            return;
        }

        if ($shipment->shiprocket_shipment_id === null) {
            $created = $shiprocket->createOrder($order);
            $shipment->fill([
                'shiprocket_order_id' => $created['order_id'],
                'shiprocket_shipment_id' => $created['shipment_id'],
                'status' => 'created',
            ])->save();
        }

        $awb = $shiprocket->assignAwb($shipment->shiprocket_shipment_id);
        $shipment->update([
            'awb_code' => $awb['awb_code'],
            'courier_name' => $awb['courier_name'],
            'status' => 'awb_assigned',
            'status_updated_at' => now(),
        ]);
    }
}
