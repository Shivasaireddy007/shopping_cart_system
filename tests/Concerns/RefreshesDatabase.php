<?php

namespace Tests\Concerns;

use Illuminate\Contracts\Console\Kernel;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Foundation\Testing\RefreshDatabaseState;

/**
 * Like RefreshDatabase, but runs "migrate" instead of "migrate:fresh".
 *
 * The storefront's tables are created by the shop package's own setup
 * command, not by Laravel migrations, so dropping every table would break
 * any test that renders a shop page. Each test still runs in a transaction
 * that is rolled back afterwards.
 */
trait RefreshesDatabase
{
    use RefreshDatabase;

    protected function refreshTestDatabase(): void
    {
        if (! RefreshDatabaseState::$migrated) {
            $this->artisan('migrate', ['--force' => true]);

            $this->app[Kernel::class]->setArtisan(null);

            RefreshDatabaseState::$migrated = true;
        }

        $this->beginDatabaseTransaction();
    }
}
