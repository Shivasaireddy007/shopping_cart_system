<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Composite indexes matching the catalog listing sorts, so MySQL can read
 * pages in index order instead of filesorting every active product.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('products', function (Blueprint $table) {
            $table->index(['is_active', 'price', 'id'], 'products_active_price_index');
            $table->index(['is_active', 'name', 'id'], 'products_active_name_index');
            $table->index(['is_active', 'category_id', 'price'], 'products_active_category_price_index');
            $table->dropIndex(['price']);
        });
    }

    public function down(): void
    {
        Schema::table('products', function (Blueprint $table) {
            $table->index('price');
            $table->dropIndex('products_active_price_index');
            $table->dropIndex('products_active_name_index');
            $table->dropIndex('products_active_category_price_index');
        });
    }
};
