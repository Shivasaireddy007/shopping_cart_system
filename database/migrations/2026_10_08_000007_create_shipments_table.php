<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('shipments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('order_id')->unique()->constrained()->cascadeOnDelete();
            $table->unsignedBigInteger('shiprocket_order_id')->nullable();
            $table->unsignedBigInteger('shiprocket_shipment_id')->nullable();
            $table->string('awb_code', 64)->nullable()->unique();
            $table->string('courier_name', 100)->nullable();
            $table->string('status', 64)->default('created');
            $table->timestamp('status_updated_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('shipments');
    }
};
