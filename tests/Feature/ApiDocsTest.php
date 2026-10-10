<?php

namespace Tests\Feature;

use Tests\TestCase;

class ApiDocsTest extends TestCase
{
    public function test_docs_page_is_public(): void
    {
        $this->get('/docs/api')->assertOk()->assertSee('Shopping Cart API');
    }

    public function test_openapi_spec_documents_jwt_and_every_api_group(): void
    {
        $spec = $this->getJson('/docs/api.json')->assertOk()->json();

        $this->assertSame('bearer', $spec['components']['securitySchemes']['http']['scheme']);
        $this->assertEqualsCanonicalizing(
            ['Auth', 'Catalog', 'Search', 'Cart', 'Checkout and orders', 'Admin', 'Webhooks'],
            array_column($spec['tags'], 'name'),
        );
        $this->assertArrayHasKey('/v1/checkout', $spec['paths']);
    }
}
