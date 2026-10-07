<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('payments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('order_id')->constrained()->cascadeOnDelete();
            $table->string('razorpay_payment_id', 64)->unique();
            $table->string('razorpay_order_id', 64)->index();
            $table->unsignedInteger('amount');        // in paise
            $table->string('status', 32);
            $table->string('method', 32)->nullable();
            $table->string('error_description')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('payments');
    }
};
