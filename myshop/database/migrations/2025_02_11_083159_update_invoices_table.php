<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

return new class extends Migration {
    public function up()
    {
        // Update existing records that have NULL invoiceno
        DB::table('invoices')->whereNull('invoiceno')->update([
            'invoiceno' => 'INV-' . Str::random(10)
        ]);

        // Alter column to set a proper default value
        Schema::table('invoices', function (Blueprint $table) {
            $table->string('invoiceno')->default(DB::raw("CONCAT('INV-', LEFT(UUID(), 10))"))->change();
        });
    }

    public function down()
    {
        Schema::table('invoices', function (Blueprint $table) {
            $table->string('invoiceno')->default(null)->change();
        });
    }
};
