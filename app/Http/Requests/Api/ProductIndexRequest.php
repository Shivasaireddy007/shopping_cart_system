<?php

namespace App\Http\Requests\Api;

use App\Services\Catalog\ProductQuery;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class ProductIndexRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'category' => ['sometimes', 'string', 'max:255'],
            'brand' => ['sometimes', 'string', 'max:100'],
            'min_price' => ['sometimes', 'integer', 'min:0'],
            'max_price' => array_filter(['sometimes', 'integer', 'min:0', $this->filled('min_price') ? 'gte:min_price' : null]),
            'in_stock' => ['sometimes', 'boolean'],
            'sort' => ['sometimes', Rule::in(array_keys(ProductQuery::SORTS))],
            'per_page' => ['sometimes', 'integer', 'between:1,50'],
            'page' => ['sometimes', 'integer', 'min:1'],
        ];
    }
}
