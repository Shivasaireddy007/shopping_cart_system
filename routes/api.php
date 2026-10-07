<?php

use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\CartController;
use App\Http\Controllers\Api\V1\CategoryController;
use App\Http\Controllers\Api\V1\ProductController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Versioned REST API for the shop. Routes are prefixed with /api and use
| the "api" middleware group. Protected routes authenticate with JWT.
|
*/

Route::prefix('v1')->name('api.v1.')->group(function () {
    Route::prefix('auth')->name('auth.')->group(function () {
        Route::post('register', [AuthController::class, 'register'])->middleware('throttle:10,1')->name('register');
        Route::post('login', [AuthController::class, 'login'])->middleware('throttle:10,1')->name('login');

        Route::middleware('auth:api')->group(function () {
            Route::get('me', [AuthController::class, 'me'])->name('me');
            Route::post('refresh', [AuthController::class, 'refresh'])->name('refresh');
            Route::post('logout', [AuthController::class, 'logout'])->name('logout');
        });
    });

    Route::get('categories', [CategoryController::class, 'index'])->name('categories.index');
    Route::get('products', [ProductController::class, 'index'])->name('products.index');
    Route::get('products/{slug}', [ProductController::class, 'show'])->name('products.show');

    Route::middleware('auth:api')->group(function () {
        Route::get('cart', [CartController::class, 'show'])->name('cart.show');
        Route::delete('cart', [CartController::class, 'clear'])->name('cart.clear');
        Route::post('cart/items', [CartController::class, 'store'])->name('cart.items.store');
        Route::patch('cart/items/{item}', [CartController::class, 'update'])->name('cart.items.update');
        Route::delete('cart/items/{item}', [CartController::class, 'destroy'])->name('cart.items.destroy');
    });
});
