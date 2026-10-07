<?php

namespace Tests;

use App\Models\User;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Http;
use PHPOpenSourceSaver\JWTAuth\JWT;

abstract class TestCase extends BaseTestCase
{
    use CreatesApplication;

    protected function setUp(): void
    {
        parent::setUp();

        // Tests must never reach Razorpay, Shiprocket or Elasticsearch for real.
        Http::preventStrayRequests();
    }

    /**
     * Issues a JWT for the user without logging them in on the guard.
     */
    protected function jwtFor(User $user): string
    {
        return $this->app->make(JWT::class)->fromUser($user);
    }

    /**
     * Every test request runs in the same process, so reset the JWT guard
     * state that a real request would start without.
     */
    public function call($method, $uri, $parameters = [], $cookies = [], $files = [], $server = [], $content = null)
    {
        $this->app['auth']->forgetGuards();
        $this->app->make(JWT::class)->unsetToken();

        return parent::call($method, $uri, $parameters, $cookies, $files, $server, $content);
    }
}
