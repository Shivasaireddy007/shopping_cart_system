<?php

namespace Database\Seeders;

use App\Models\Category;
use Database\Factories\ProductFactory;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Seeds a large catalog for load testing:
 *   SEED_PRODUCTS=100000 php -d memory_limit=1G artisan db:seed --class=CatalogSeeder
 *
 * Rows are bulk inserted, bypassing model events, so seeding does not queue
 * one search sync per product. Run search:reindex afterwards.
 */
class CatalogSeeder extends Seeder
{
    private const CATEGORIES = [
        'Running Shoes', 'Sneakers', 'Formal Shoes', 'Sandals', 'Boots', 'T-Shirts', 'Shirts', 'Jeans',
        'Trousers', 'Shorts', 'Jackets', 'Hoodies', 'Track Pants', 'Kurtas', 'Sarees', 'Dresses',
        'Watches', 'Wallets', 'Belts', 'Backpacks', 'Sunglasses', 'Caps', 'Socks', 'Sportswear',
    ];

    public function run(): void
    {
        $total = (int) env('SEED_PRODUCTS', 100000);
        $chunk = 1000;

        $categoryIds = collect(self::CATEGORIES)->map(fn (string $name) => Category::firstOrCreate(
            ['slug' => Str::slug($name)],
            ['name' => $name],
        )->id)->all();

        $factory = ProductFactory::new();
        $now = now();

        for ($done = 0; $done < $total; $done += $chunk) {
            $rows = [];

            for ($i = 0; $i < min($chunk, $total - $done); $i++) {
                $row = $factory->raw(['category_id' => $categoryIds[array_rand($categoryIds)]]);
                $row['attributes'] = json_encode($row['attributes']);
                $row['created_at'] = $row['updated_at'] = $now->copy()->subMinutes(random_int(0, 525600));
                $rows[] = $row;
            }

            DB::table('products')->insert($rows);
            $this->command?->getOutput()->write("\r  Seeded ".($done + count($rows))." / {$total} products");
        }

        $this->command?->newLine();
    }
}
