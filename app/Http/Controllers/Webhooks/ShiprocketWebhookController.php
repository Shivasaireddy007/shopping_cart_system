<?php

namespace App\Http\Controllers\Webhooks;

use App\Http\Controllers\Controller;
use App\Models\WebhookEvent;
use App\Services\Shipping\ShipmentStatusUpdater;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

#[Group('Webhooks', weight: 7)]
class ShiprocketWebhookController extends Controller
{
    /**
     * Receive Shiprocket shipment status updates.
     *
     * Authenticated with the `x-api-key` header. Orders only move forward
     * (paid → shipped → delivered), so late or repeated updates are ignored.
     */
    public function __invoke(Request $request, ShipmentStatusUpdater $updater): JsonResponse
    {
        $token = (string) config('services.shiprocket.webhook_token');

        if ($token === '' || ! hash_equals($token, (string) $request->header('x-api-key'))) {
            return response()->json(['message' => 'Unauthorized.'], 401);
        }

        $awb = (string) $request->input('awb');
        $status = (string) $request->input('current_status');

        if ($awb === '' || $status === '') {
            return response()->json(['status' => 'ignored']);
        }

        // Shiprocket sends no event id, so the AWB and status identify a delivery.
        $isNew = WebhookEvent::insertOrIgnore([
            'provider' => 'shiprocket',
            'event_id' => hash('sha256', $awb.'|'.strtoupper($status)),
            'type' => strtolower($status),
            'processed_at' => now(),
            'created_at' => now(),
            'updated_at' => now(),
        ]) === 1;

        if ($isNew) {
            $updater->apply($awb, $status);
        }

        return response()->json(['status' => $isNew ? 'ok' : 'duplicate']);
    }
}
