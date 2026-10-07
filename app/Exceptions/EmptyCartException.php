<?php

namespace App\Exceptions;

use Illuminate\Http\JsonResponse;
use RuntimeException;

class EmptyCartException extends RuntimeException
{
    public function __construct()
    {
        parent::__construct('Your cart is empty.');
    }

    public function render(): JsonResponse
    {
        return response()->json(['message' => $this->getMessage()], 422);
    }
}
