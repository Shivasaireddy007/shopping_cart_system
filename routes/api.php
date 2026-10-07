<?php

use App\Http\Controllers\Api\V1\AuthController;
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
});
