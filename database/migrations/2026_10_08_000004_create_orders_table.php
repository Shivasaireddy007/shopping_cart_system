<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('orders', function (Blueprint $table) {
            $table->id();
            $table->string('number', 32)->unique();
            $table->foreignId('user_id')->constrained()->restrictOnDelete();
            $table->string('status', 32)->index();
            $table->unsignedInteger('subtotal');      // in paise
            $table->unsignedInteger('shipping_fee');  // in paise
            $table->unsignedInteger('total');         // in paise
            $table->char('currency', 3)->default('INR');
            $table->json('shipping_address');
            $table->string('razorpay_order_id', 64)->nullable()->unique();
            $table->timestamp('paid_at')->nullable();
            $table->timestamp('cancelled_at')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'created_at']);
        });

        Schema::create('order_items', function (Blueprint $table) {
            $table->id();
            $table->foreignId('order_id')->constrained()->cascadeOnDelete();
            $table->foreignId('product_id')->nullable()->constrained()->nullOnDelete();
            $table->string('sku', 64);
            $table->string('name');
            $table->unsignedInteger('unit_price');    // in paise, at time of order
            $table->unsignedSmallInteger('quantity');
            $table->unsignedInteger('line_total');    // in paise
            $table->unsignedInteger('weight_grams');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('order_items');
        Schema::dropIfExists('orders');
    }
};
