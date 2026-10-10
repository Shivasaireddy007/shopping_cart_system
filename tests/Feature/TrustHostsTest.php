<?php

namespace Tests\Feature;

use App\Http\Middleware\TrustHosts;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class TrustHostsTest extends TestCase
{
    use RefreshesDatabase;

    private function trustedFor(string $url): array
    {
        $middleware = new class($this->app) extends TrustHosts
        {
            public function trustedFor(Request $request): array
            {
                return $this->trusted($request);
            }
        };

        return $middleware->trustedFor(Request::create($url));
    }

    public function test_a_registered_shop_domain_is_trusted_as_a_host_pattern(): void
    {
        $code = DB::table('mshop_locale_site')->value('code');

        $hosts = $this->trustedFor("http://{$code}/");

        $this->assertContains('^'.preg_quote($code).'$', $hosts);
        $this->assertContainsOnly('string', array_filter($hosts));
    }

    public function test_an_unknown_host_is_not_added(): void
    {
        $hosts = $this->trustedFor('http://evil.example/');

        $this->assertNotContains('^evil\.example$', $hosts);
        $this->assertContainsOnly('string', array_filter($hosts));
    }
}
