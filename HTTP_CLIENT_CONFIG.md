# HTTP Client Configuration

The Wanderer plugin uses a configurable HTTP client with automatic retry logic for increased reliability when communicating with the Wanderer API.

## Configuration Settings

Add these settings to your Alliance Auth `settings/local.py` file:

### API Timeouts

Control how long to wait for Wanderer API responses:

```python
# Default timeout for API calls (in seconds)
# Used for most operations: get members, add/remove characters, etc.
# Default: 10 seconds
WANDERER_API_TIMEOUT = 10

# Timeout for potentially long-running operations (in seconds)
# Can be used for operations that might take longer
# Default: 30 seconds
WANDERER_API_LONG_TIMEOUT = 30
```

**Recommendations:**
- **Default (10s):** Sufficient for most operations under normal network conditions
- **Long (30s):** Reserved for operations that might involve multiple characters or slow networks
- **Production:** Monitor actual response times and adjust accordingly based on your environment

### Retry Configuration

Control automatic retry behavior for failed API calls:

```python
# Number of retry attempts before giving up
# Default: 3 retries
WANDERER_API_RETRY_TOTAL = 3

# Backoff factor for exponential backoff
# Delay between retries = backoff_factor * (2 ** retry_number)
# 0.5 means: wait 0.5s, then 1s, then 2s between retries
# Default: 0.5
WANDERER_API_RETRY_BACKOFF = 0.5

# HTTP status codes that trigger automatic retries
# Default: (500, 502, 503, 504, 429)
WANDERER_API_RETRY_STATUS_CODES = (
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
    429,  # Too Many Requests (rate limiting)
)
```

### Configuration Examples

#### Aggressive Retries (Unreliable Networks)

Use this configuration if your network connection to Wanderer is unreliable:

```python
WANDERER_API_RETRY_TOTAL = 5
WANDERER_API_RETRY_BACKOFF = 1.0  # Wait: 1s, 2s, 4s, 8s, 16s
WANDERER_API_TIMEOUT = 15  # Longer timeout
```

#### Conservative Retries (Stable Environments)

Use this configuration for stable environments with reliable networks:

```python
WANDERER_API_RETRY_TOTAL = 2
WANDERER_API_RETRY_BACKOFF = 0.3  # Wait: 0.3s, 0.6s
WANDERER_API_TIMEOUT = 5  # Shorter timeout
```

#### No Retries (Debugging)

Disable retries during debugging to see failures immediately:

```python
WANDERER_API_RETRY_TOTAL = 0
```

## How It Works

### Retry Behavior

The HTTP client automatically retries failed requests with exponential backoff:

1. **Initial Request:** First attempt is made
2. **Retry #1:** If failed, wait `backoff_factor * (2^0)` seconds (0.5s default)
3. **Retry #2:** If failed, wait `backoff_factor * (2^1)` seconds (1.0s default)
4. **Retry #3:** If failed, wait `backoff_factor * (2^2)` seconds (2.0s default)
5. **Final:** Either succeeds or raises exception after all retries exhausted

**Example Timeline for a Failed Request:**

With default settings (3 retries, 0.5s backoff):
```
0.0s  - Initial request fails with 503 Service Unavailable
0.5s  - Retry #1 fails with 503
1.5s  - Retry #2 fails with 503  (waited 1.0s)
3.5s  - Retry #3 succeeds        (waited 2.0s)
```

### Retry Conditions

Requests are automatically retried when:
- **Server Errors:** 500, 502, 503, 504 status codes
- **Rate Limiting:** 429 status code
- **Network Issues:** Connection errors, timeouts (if configured)

Requests are **NOT** retried for:
- **Client Errors:** 400, 401, 403, 404 (these indicate programming errors or auth issues)
- **Success Responses:** 200, 201, 204 (operation succeeded)

### Timeout Behavior

- **Read Operations (GET):** Use `WANDERER_API_TIMEOUT` (default 10s)
- **Write Operations (POST, PUT, DELETE):** Use `WANDERER_API_TIMEOUT` (default 10s)
- **Long Operations:** Can manually specify longer timeout if needed

Timeouts apply to **each individual request**, including retries. If a request times out, it will be retried if configured.

## Monitoring

### Logging

Enable DEBUG logging to monitor HTTP client behavior:

```python
# settings/local.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/allianceauth/wanderer.log',
        },
    },
    'loggers': {
        'wanderer': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

With DEBUG logging enabled, you'll see:
- Every API call with URL and timeout
- Response status codes
- Retry attempts with backoff delays
- Timeout and connection errors

### Metrics to Track

Monitor these metrics to optimize your configuration:

1. **API Response Times**
   - Average response time
   - 95th percentile response time
   - Maximum response time

2. **Retry Rates**
   - Percentage of requests that required retries
   - Number of retries per endpoint
   - Success rate after retries

3. **Timeout Rates**
   - Number of timeouts per hour
   - Which endpoints timeout most frequently

4. **Error Rates**
   - Total API errors per hour
   - Breakdown by error type (500, 503, timeout, etc.)

## Troubleshooting

### Frequent Timeouts

**Symptoms:** Many timeout errors in logs

**Solutions:**
1. Increase `WANDERER_API_TIMEOUT` to 15-20 seconds
2. Check network latency to Wanderer instance
3. Verify Wanderer server performance

### Frequent 503 Errors

**Symptoms:** Many 503 Service Unavailable errors

**Solutions:**
1. Increase retry backoff: `WANDERER_API_RETRY_BACKOFF = 1.0`
2. Check Wanderer server load
3. Consider rate limiting on your end

### Retries Not Working

**Symptoms:** Errors not being retried automatically

**Solutions:**
1. Verify `WANDERER_API_RETRY_TOTAL > 0`
2. Check that error status code is in `WANDERER_API_RETRY_STATUS_CODES`
3. Enable DEBUG logging to see retry attempts

### Slow API Operations

**Symptoms:** Operations take too long

**Solutions:**
1. Check if unnecessary retries are happening (reduce retry count)
2. Reduce timeout if requests are hanging
3. Enable caching (see CACHE_CONFIG.md)

## Advanced Configuration

### Custom Retry Logic Per Endpoint

The HTTP client applies the same retry logic to all endpoints. If you need custom behavior for specific endpoints, you can:

1. Create a custom wrapper function
2. Call the HTTP client with specific timeout values
3. Handle retries manually in your code

### Integration with Other Tools

The HTTP client uses Python `requests` library and `urllib3` for retries. It's compatible with:
- HTTP proxies
- SSL certificate verification
- Custom headers
- Session management

## See Also

- [CACHE_CONFIG.md](CACHE_CONFIG.md) - Cache configuration for performance
- [README.md](README.md) - General plugin documentation
- [Wanderer API Documentation](https://wanderer.ltd/news/api) - Official API docs
