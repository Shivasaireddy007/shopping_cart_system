<?php

namespace App\Http\Requests\Api;

use Illuminate\Foundation\Http\FormRequest;

class CheckoutRequest extends FormRequest
{
    public function rules(): array
    {
        return [
            'shipping_address' => ['required', 'array'],
            'shipping_address.name' => ['required', 'string', 'max:100'],
            'shipping_address.phone' => ['required', 'regex:/^[6-9]\d{9}$/'],
            'shipping_address.line1' => ['required', 'string', 'max:255'],
            'shipping_address.line2' => ['nullable', 'string', 'max:255'],
            'shipping_address.city' => ['required', 'string', 'max:100'],
            'shipping_address.state' => ['required', 'string', 'max:100'],
            'shipping_address.pincode' => ['required', 'regex:/^[1-9]\d{5}$/'],
        ];
    }

    public function messages(): array
    {
        return [
            'shipping_address.phone.regex' => 'Enter a valid 10-digit Indian mobile number.',
            'shipping_address.pincode.regex' => 'Enter a valid 6-digit PIN code.',
        ];
    }
}
