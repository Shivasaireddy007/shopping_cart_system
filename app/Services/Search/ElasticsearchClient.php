<?php

namespace App\Services\Search;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

/**
 * Minimal Elasticsearch REST client built on Laravel's HTTP client.
 */
class ElasticsearchClient
{
    public function __construct(private readonly string $host) {}

    public static function fromConfig(): self
    {
        return new self((string) config('services.elasticsearch.host'));
    }

    public function get(string $path): Response
    {
        return $this->http()->get($path);
    }

    public function put(string $path, array $body = []): Response
    {
        return $this->http()->put($path, $body ?: (object) []);
    }

    public function post(string $path, array $body = []): Response
    {
        // Some endpoints (e.g. _refresh) reject any request body, even "[]".
        return $body === []
            ? $this->http()->send('POST', $path)
            : $this->http()->post($path, $body);
    }

    public function delete(string $path): Response
    {
        return $this->http()->delete($path);
    }

    /**
     * Sends a _bulk request. Each action is an [action, document|null] pair.
     *
     * @param  array<int, array{0: array, 1: array|null}>  $actions
     */
    public function bulk(array $actions): Response
    {
        $ndjson = '';

        foreach ($actions as [$action, $document]) {
            $ndjson .= json_encode($action)."\n";

            if ($document !== null) {
                $ndjson .= json_encode($document)."\n";
            }
        }

        return $this->http()
            ->withBody($ndjson, 'application/x-ndjson')
            ->post('/_bulk');
    }

    private function http(): PendingRequest
    {
        return Http::baseUrl($this->host)->acceptJson()->timeout(5)->connectTimeout(2);
    }
}
