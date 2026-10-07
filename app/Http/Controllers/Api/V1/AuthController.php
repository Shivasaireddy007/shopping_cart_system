<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\LoginRequest;
use App\Http\Requests\Api\RegisterRequest;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Hash;

class AuthController extends Controller
{
    public function register(RegisterRequest $request): JsonResponse
    {
        $user = User::create([
            'name' => $request->validated('name'),
            'email' => $request->validated('email'),
            'password' => Hash::make($request->validated('password')),
        ]);

        return $this->tokenResponse(auth('api')->login($user), 201);
    }

    public function login(LoginRequest $request): JsonResponse
    {
        if (! $token = auth('api')->attempt($request->validated())) {
            return response()->json(['message' => 'Invalid credentials.'], 401);
        }

        return $this->tokenResponse($token);
    }

    public function me(): JsonResponse
    {
        return response()->json(['data' => auth('api')->user()]);
    }

    public function refresh(): JsonResponse
    {
        return $this->tokenResponse(auth('api')->refresh());
    }

    public function logout(): JsonResponse
    {
        auth('api')->logout();

        return response()->json(['message' => 'Logged out.']);
    }

    private function tokenResponse(string $token, int $status = 200): JsonResponse
    {
        return response()->json([
            'access_token' => $token,
            'token_type' => 'bearer',
            'expires_in' => auth('api')->factory()->getTTL() * 60,
        ], $status);
    }
}
