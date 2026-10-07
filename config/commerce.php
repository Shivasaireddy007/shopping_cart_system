<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Shipping charges
    |--------------------------------------------------------------------------
    |
    | All amounts are in paise. Orders at or above the free shipping
    | threshold ship for free, everything else pays the flat fee.
    |
    */

    'shipping' => [
        'flat_fee' => (int) env('SHIPPING_FLAT_FEE', 4900),
        'free_above' => (int) env('SHIPPING_FREE_ABOVE', 99900),
    ],

    'cart' => [
        'max_quantity_per_item' => 10,
    ],

];
