<?php

namespace App\Http\Controllers\Auth;

use Aimeos\Bootstrap;
use Aimeos\MShop;
use Aimeos\Setup;
use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Auth\Events\Registered;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\Rules;
use Illuminate\Validation\ValidationException;
use Illuminate\View\View;

class RegisteredUserController extends Controller
{
    /**
     * Display the registration view.
     */
    public function create(): View
    {
        return view('auth.register');
    }

    /**
     * Handle an incoming registration request.
     *
     *
     * @throws ValidationException
     */
    public function store(Request $request): RedirectResponse
    {
        $this->check($request);

        $user = $this->user($request);

        event(new Registered($user));

        Auth::login($user);

        $params = config('app.shop_multishop') && config('app.shop_registration') && $request->code ? ['site' => $request->code] : [];

        return redirect(airoute('aimeos_home', $params));
    }

    /**
     * Returns the site ID the user should be associated to
     *
     * @return string Site ID
     */
    protected function siteid(Request $request): string
    {
        $context = app('aimeos.context')->get();
        $manager = MShop::create($context, 'locale/site');

        $site = $request->route('site', $request->input('site', config('shop.mshop.locale.site', 'default')));
        $root = $manager->find($site);
        $siteId = $root->getSiteId();

        if (config('app.shop_multishop') && config('app.shop_registration')) {
            $code = $request->code;
            $item = $manager->create()->setCode($code)->setLabel($code)->setStatus(1);
            $site = $manager->insert($item, $root->getId());

            Setup::use(new Bootstrap)->context($context)->verbose('')->up($code);

            if ($site->getSiteId() === $site->getId().'.') {
                $manager = MShop::create($context, 'locale');
                $locale = $manager->create()->setSiteId($site->getSiteId())->setLanguageId('en')->setCurrencyId('USD');
                $manager->save($locale);
            }

            $siteId = $site->getSiteId();
        }

        return $siteId;
    }

    /**
     * Returns the newly created user
     *
     * @return User $user
     */
    protected function user(Request $request): User
    {
        $user = User::create([
            'name' => strip_tags($request->code ?? $request->name),
            'email' => $request->email,
            'password' => Hash::make($request->password),
            'siteid' => $this->siteid($request),
        ]);

        if (config('app.shop_multishop') && config('app.shop_registration')) {
            $context = app('aimeos.context')->get();
            $context->setLocale(MShop::create($context, 'locale')->bootstrap($request->code));

            $manager = MShop::create($context, 'customer');

            $group = MShop::create($context, 'group')->find(config('app.shop_permission', 'admin'));
            $customer = $manager->get($user->id, ['group'])->setGroups([$group->getId() => $group->getCode()]);

            $manager->save($customer);
        }

        return $user;
    }

    /**
     * Validates the values entered for the user
     *
     *
     * @throws ValidationException
     */
    protected function check(Request $request)
    {
        $rules = [
            'email' => ['required', 'string', 'email', 'max:255', 'unique:users'],
            'password' => ['required', 'confirmed', Rules\Password::defaults()],
        ];

        if (config('app.shop_multishop') && config('app.shop_registration')) {
            $rules['code'] = ['required', 'string', 'max:255', 'unique:mshop_locale_site', 'regex:/^[a-z0-9\-]+(\.[a-z0-9\-]+)?$/i'];
        } else {
            $rules['name'] = ['required', 'string', 'max:255'];
        }

        $request->validate($rules);
    }
}
