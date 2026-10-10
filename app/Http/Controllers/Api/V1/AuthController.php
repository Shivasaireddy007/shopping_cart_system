<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\LoginRequest;
use App\Http\Requests\Api\RegisterRequest;
use App\Models\User;
use Dedoc\Scramble\Attributes\Group;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Hash;
use PHPOpenSourceSaver\JWTAuth\JWTGuard;

#[Group('Auth', weight: 1)]
class AuthController extends Controller
{
    /**
     * Register a customer account and get a JWT.
     */
    public function register(RegisterRequest $request): JsonResponse
    {
        $user = User::create([
            'name' => $request->validated('name'),
            'email' => $request->validated('email'),
            'password' => Hash::make($request->validated('password')),
        ]);

        return $this->tokenResponse($this->guard()->login($user), 201);
    }

    /**
     * Log in with email and password and get a JWT.
     */
    public function login(LoginRequest $request): JsonResponse
    {
        $token = $this->guard()->attempt($request->validated());

        if (! is_string($token)) {
            return response()->json(['message' => 'Invalid credentials.'], 401);
        }

        return $this->tokenResponse($token);
    }

    /**
     * Get the logged-in user.
     */
    public function me(): JsonResponse
    {
        return response()->json(['data' => $this->guard()->user()]);
    }

    /**
     * Exchange the current token for a new one.
     */
    public function refresh(): JsonResponse
    {
        return $this->tokenResponse($this->guard()->refresh());
    }

    /**
     * Revoke the current token.
     */
    public function logout(): JsonResponse
    {
        $this->guard()->logout();

        return response()->json(['message' => 'Logged out.']);
    }

    private function guard(): JWTGuard
    {
        /** @var JWTGuard */
        return auth('api');
    }

    private function tokenResponse(string $token, int $status = 200): JsonResponse
    {
        return response()->json([
            'access_token' => $token,
            'token_type' => 'bearer',
            'expires_in' => $this->guard()->factory()->getTTL() * 60,
        ], $status);
    }
}
