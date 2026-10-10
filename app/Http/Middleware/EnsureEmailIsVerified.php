<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Redirect;

class EnsureEmailIsVerified
{
    /**
     * Handle an incoming request.
     *
     * @param  Request  $request
     * @param  string|null  $redirectToRoute
     * @return Response|RedirectResponse|null
     */
    public function handle($request, Closure $next, $redirectToRoute = null)
    {
        if (! $request->user() || ! $request->user()->hasVerifiedEmail()) {
            $params = [];

            if (config('app.shop_multilocale')) {
                $params['locale'] = $request->route('locale', $request->input('locale', app()->getLocale()));
            }

            if (config('app.shop_multishop')) {
                $params['site'] = $request->route('site', $request->input('site', config('shop.mshop.locale.site', 'default')));
            }

            return $request->expectsJson()
                ? abort(403, 'Your email address is not verified.')
                : Redirect::guest(airoute($redirectToRoute ?: 'verification.notice', $params));
        }

        return $next($request);
    }
}
