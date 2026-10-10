<?php

namespace App\Services\Search;

use App\Models\Product;
use Illuminate\Support\LazyCollection;

/**
 * Manages the products search index. The configured index name is an alias
 * pointing at a versioned index, so a full reindex builds a new index in the
 * background and swaps the alias atomically.
 */
class ProductIndex
{
    public function __construct(private readonly ElasticsearchClient $es) {}

    public function alias(): string
    {
        return config('services.elasticsearch.index');
    }

    /**
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'settings' => [
                'number_of_shards' => 1,
                'number_of_replicas' => 0,
            ],
            'mappings' => [
                'dynamic' => 'strict',
                'properties' => [
                    'id' => ['type' => 'long'],
                    'sku' => ['type' => 'keyword'],
                    'name' => ['type' => 'text', 'analyzer' => 'english', 'fields' => ['raw' => ['type' => 'keyword']]],
                    'description' => ['type' => 'text', 'analyzer' => 'english'],
                    'brand' => ['type' => 'keyword'],
                    'category' => ['type' => 'keyword'],
                    'color' => ['type' => 'keyword'],
                    'size' => ['type' => 'keyword'],
                    'price' => ['type' => 'long'],
                    'in_stock' => ['type' => 'boolean'],
                    'created_at' => ['type' => 'date'],
                ],
            ],
        ];
    }

    /**
     * @return array<string, mixed>
     */
    public function document(Product $product): array
    {
        return [
            'id' => $product->id,
            'sku' => $product->sku,
            'name' => $product->name,
            'description' => $product->description,
            'brand' => $product->brand,
            'category' => $product->category->slug,
            'color' => $product->attributes['color'] ?? null,
            'size' => $product->attributes['size'] ?? null,
            'price' => $product->price,
            'in_stock' => $product->stock > 0,
            'created_at' => $product->created_at->toIso8601String(),
        ];
    }

    /**
     * Indexes an active product, or removes it from the index if it is inactive.
     */
    public function sync(Product $product): void
    {
        if (! $product->is_active) {
            $this->remove($product->id);

            return;
        }

        $this->es->put("/{$this->alias()}/_doc/{$product->id}", $this->document($product->loadMissing('category')))->throw();
    }

    public function remove(int $productId): void
    {
        $response = $this->es->delete("/{$this->alias()}/_doc/{$productId}");

        if ($response->status() !== 404) {
            $response->throw();
        }
    }

    /**
     * Rebuilds the whole index into a new versioned index and points the
     * alias at it. Returns the number of products indexed.
     */
    public function rebuild(int $chunk = 1000): int
    {
        $alias = $this->alias();
        $index = $alias.'_'.now()->format('YmdHis');

        $this->es->put("/{$index}", $this->definition())->throw();

        try {
            $count = $this->fill($index, $chunk);
            $this->es->post("/{$index}/_refresh")->throw();
            $this->swapAlias($alias, $index);
        } catch (\Throwable $e) {
            // Don't leave a half-built index behind; the alias still serves the old one.
            $this->es->delete("/{$index}");

            throw $e;
        }

        return $count;
    }

    private function fill(string $index, int $chunk): int
    {
        $count = 0;
        Product::active()->with('category')->lazyById($chunk)
            ->chunk($chunk)
            ->each(function (LazyCollection $products) use ($index, &$count) {
                $actions = $products->map(fn (Product $product) => [
                    ['index' => ['_index' => $index, '_id' => $product->id]],
                    $this->document($product),
                ])->values()->all();

                $response = $this->es->bulk($actions)->throw();

                if ($response->json('errors')) {
                    throw new \RuntimeException('Bulk indexing reported errors: '.json_encode(array_slice($response->json('items'), 0, 3)));
                }

                $count += count($actions);
            });

        return $count;
    }

    private function swapAlias(string $alias, string $index): void
    {
        $current = $this->es->get("/_alias/{$alias}");
        $old = $current->successful() ? array_keys($current->json()) : [];

        // A plain index with the alias name (e.g. from a first run) must go.
        if ($this->es->get("/{$alias}")->successful() && ! $current->successful()) {
            $this->es->delete("/{$alias}")->throw();
        }

        $actions = [['add' => ['index' => $index, 'alias' => $alias]]];
        foreach ($old as $oldIndex) {
            $actions[] = ['remove_index' => ['index' => $oldIndex]];
        }

        $this->es->post('/_aliases', ['actions' => $actions])->throw();
    }
}
