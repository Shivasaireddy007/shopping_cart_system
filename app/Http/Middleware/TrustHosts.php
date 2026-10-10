<?php

namespace App\Http\Middleware;

use Illuminate\Http\Middleware\TrustHosts as Middleware;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\DB;

class TrustHosts extends Middleware
{
    /**
     * Handle the incoming request.
     *
     * @param  \Closure  $next
     * @return Response
     */
    public function handle(Request $request, $next)
    {
        if ($this->shouldSpecifyTrustedHosts()) {
            Request::setTrustedHosts(array_filter($this->trusted($request)));
        }

        return $next($request);
    }

    public function hosts()
    {
        return [];
    }

    /**
     * Get the host patterns that should be trusted.
     *
     * @return array<int, string|null>
     */
    protected function trusted(Request $request)
    {
        $domains = [$this->allSubdomainsOfApplicationUrl(), '10\.[0-9]+\.[0-9]+\.[0-9]+']; // private IPs for Kubernetes probe checks

        // Trust custom shop domains registered as site codes.
        if (($domain = $request->host()) && DB::table('mshop_locale_site')->where('code', $domain)->exists()) {
            $domains[] = '^'.preg_quote($domain).'$';
        }

        return $domains;
    }
}
