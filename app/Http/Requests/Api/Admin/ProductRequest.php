<?php

namespace App\Http\Requests\Api\Admin;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

/**
 * Validates product create (POST) and partial update (PATCH) requests.
 */
class ProductRequest extends FormRequest
{
    protected function prepareForValidation(): void
    {
        if ($this->isMethod('post') && ! $this->filled('slug') && $this->filled('name')) {
            $this->merge(['slug' => Str::slug($this->input('name')).'-'.Str::lower(Str::random(6))]);
        }
    }

    public function rules(): array
    {
        $product = $this->route('product');
        $required = $this->isMethod('post') ? 'required' : 'sometimes';

        return [
            'category_id' => [$required, 'integer', 'exists:categories,id'],
            'sku' => [$required, 'string', 'max:64', 'alpha_dash', Rule::unique('products', 'sku')->ignore($product)],
            'name' => [$required, 'string', 'max:255'],
            'slug' => [$required, 'string', 'max:255', 'alpha_dash', Rule::unique('products', 'slug')->ignore($product)],
            'description' => ['sometimes', 'nullable', 'string', 'max:5000'],
            'brand' => [$required, 'string', 'max:100'],
            'price' => [$required, 'integer', 'min:100'],
            'mrp' => ['sometimes', 'nullable', 'integer', 'gte:price'],
            'stock' => [$required, 'integer', 'min:0'],
            'weight_grams' => ['sometimes', 'integer', 'between:1,50000'],
            'attributes' => ['sometimes', 'array'],
            'attributes.color' => ['sometimes', 'string', 'max:50'],
            'attributes.size' => ['sometimes', 'string', 'max:20'],
            'is_active' => ['sometimes', 'boolean'],
        ];
    }
}
