<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class AuthTest extends TestCase
{
    use RefreshesDatabase;

    public function test_user_can_register_and_receives_a_token(): void
    {
        $response = $this->postJson('/api/v1/auth/register', [
            'name' => 'Asha',
            'email' => 'asha@example.com',
            'password' => 'secret-password',
            'password_confirmation' => 'secret-password',
        ]);

        $response->assertCreated()->assertJsonStructure(['access_token', 'token_type', 'expires_in']);
        $this->assertDatabaseHas('users', ['email' => 'asha@example.com']);
    }

    public function test_user_can_log_in_with_valid_credentials(): void
    {
        $user = User::factory()->create();

        $this->postJson('/api/v1/auth/login', ['email' => $user->email, 'password' => 'password'])
            ->assertOk()
            ->assertJsonPath('token_type', 'bearer');
    }

    public function test_login_fails_with_wrong_password(): void
    {
        $user = User::factory()->create();

        $this->postJson('/api/v1/auth/login', ['email' => $user->email, 'password' => 'wrong'])
            ->assertUnauthorized();
    }

    public function test_me_returns_the_authenticated_user(): void
    {
        $user = User::factory()->create();
        $token = $this->jwtFor($user);

        $this->withToken($token)->getJson('/api/v1/auth/me')
            ->assertOk()
            ->assertJsonPath('data.email', $user->email);
    }

    public function test_me_requires_a_token(): void
    {
        $this->getJson('/api/v1/auth/me')->assertUnauthorized();
    }

    public function test_logged_out_token_is_rejected(): void
    {
        $user = User::factory()->create();
        $token = $this->jwtFor($user);

        $this->withToken($token)->postJson('/api/v1/auth/logout')->assertOk();

        $this->withToken($token)->getJson('/api/v1/auth/me')->assertUnauthorized();
    }

    public function test_token_can_be_refreshed(): void
    {
        $user = User::factory()->create();
        $token = $this->jwtFor($user);

        $response = $this->withToken($token)->postJson('/api/v1/auth/refresh')->assertOk();

        $this->assertNotSame($token, $response->json('access_token'));
    }
}
