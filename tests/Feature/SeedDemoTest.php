<?php

namespace Tests\Feature;

use App\Models\Product;
use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Tests\Concerns\RefreshesDatabase;
use Tests\TestCase;

class SeedDemoTest extends TestCase
{
    use RefreshesDatabase;

    public function test_seeds_an_empty_catalog_and_a_demo_customer_once(): void
    {
        $this->artisan('demo:seed', ['--products' => 30])->assertSuccessful();
        $this->artisan('demo:seed', ['--products' => 30])->assertSuccessful();

        $this->assertSame(30, Product::count());
        $user = User::where('email', 'demo@shoppingcart.test')->sole();
        $this->assertTrue(Hash::check('demo-password', $user->password));
        $this->assertFalse($user->is_admin);
    }
}
