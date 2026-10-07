<?php

namespace App\Http\Requests\Api;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class SearchRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'q' => ['sometimes', 'nullable', 'string', 'max:200'],
            'brand' => ['sometimes', 'array', 'max:20'],
            'brand.*' => ['string', 'max:100'],
            'category' => ['sometimes', 'array', 'max:20'],
            'category.*' => ['string', 'max:255'],
            'color' => ['sometimes', 'array', 'max:20'],
            'color.*' => ['string', 'max:50'],
            'size' => ['sometimes', 'array', 'max:20'],
            'size.*' => ['string', 'max:20'],
            'min_price' => ['sometimes', 'integer', 'min:0'],
            'max_price' => array_filter(['sometimes', 'integer', 'min:0', $this->filled('min_price') ? 'gte:min_price' : null]),
            'in_stock' => ['sometimes', 'boolean'],
            'sort' => ['sometimes', Rule::in(['relevance', 'newest', 'price_asc', 'price_desc'])],
            'page' => ['sometimes', 'integer', 'min:1', 'max:400'],
            'per_page' => ['sometimes', 'integer', 'between:1,50'],
        ];
    }
}
