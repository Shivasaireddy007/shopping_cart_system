<?php

namespace App\Console\Commands;

use App\Models\Product;
use App\Models\User;
use Database\Seeders\CatalogSeeder;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Hash;

class SeedDemo extends Command
{
    protected $signature = 'demo:seed {--products=1000 : Products to create when the catalog is empty}';

    protected $description = 'Fill an empty database with a demo catalog and a demo customer (safe to run on every deploy)';

    public function handle(): int
    {
        if (Product::exists()) {
            $this->info('Catalog already has products, skipping.');
        } else {
            $seeder = $this->laravel->make(CatalogSeeder::class);
            $seeder->total = (int) $this->option('products');
            $seeder->setCommand($this)->run();
            $this->info("Seeded {$seeder->total} products.");
        }

        $email = config('commerce.demo.email');

        User::firstOrCreate(['email' => $email], [
            'name' => 'Demo Customer',
            'password' => Hash::make(config('commerce.demo.password')),
            'email_verified_at' => now(),
        ]);

        $this->info("Demo customer: {$email}");

        return self::SUCCESS;
    }
}
