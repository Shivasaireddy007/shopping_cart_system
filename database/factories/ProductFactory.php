<?php

namespace Database\Factories;

use App\Models\Category;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Product>
 */
class ProductFactory extends Factory
{
    private const BRANDS = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Bata', 'Woodland', 'Campus', 'Sparx'];
    private const COLORS = ['black', 'white', 'red', 'blue', 'green', 'grey'];
    private const SIZES = ['S', 'M', 'L', 'XL'];

    public function definition(): array
    {
        $name = Str::title($this->faker->words(3, true));
        $price = $this->faker->numberBetween(199, 9999) * 100;

        return [
            'category_id' => Category::factory(),
            'sku' => 'SKU-'.Str::upper(Str::random(10)),
            'name' => $name,
            'slug' => Str::slug($name).'-'.Str::lower(Str::random(6)),
            'description' => $this->faker->paragraph(),
            'brand' => $this->faker->randomElement(self::BRANDS),
            'price' => $price,
            'mrp' => (int) round($price * 1.25),
            'stock' => $this->faker->numberBetween(0, 200),
            'weight_grams' => $this->faker->numberBetween(100, 2000),
            'attributes' => [
                'color' => $this->faker->randomElement(self::COLORS),
                'size' => $this->faker->randomElement(self::SIZES),
            ],
            'is_active' => true,
        ];
    }

    public function outOfStock(): static
    {
        return $this->state(['stock' => 0]);
    }

    public function inactive(): static
    {
        return $this->state(['is_active' => false]);
    }
}
