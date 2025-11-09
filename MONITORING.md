# Monitoring and Observability Guide

This guide covers monitoring recommendations for the aa-wanderer-map plugin to ensure optimal performance and reliability.

## Table of Contents

1. [Key Metrics](#key-metrics)
2. [Logging Configuration](#logging-configuration)
3. [Performance Monitoring](#performance-monitoring)
4. [Alert Configuration](#alert-configuration)
5. [Troubleshooting](#troubleshooting)

## Key Metrics

### 1. API Response Times

Track how long Wanderer API calls take to complete.

**What to Monitor:**
- Average response time per endpoint
- 95th percentile response time
- Maximum response time
- Response time distribution

**Target Values:**
- Average: < 1 second
- 95th percentile: < 2 seconds
- Maximum: < 10 seconds

**How to Monitor:**

```python
# Add timing to your Django middleware or use Django Debug Toolbar
import time
from django.utils.deprecation import MiddlewareMixin

class WandererAPITimingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.wanderer_start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, 'wanderer_start_time'):
            duration = time.time() - request.wanderer_start_time
            # Log or send to metrics system
            logger.info(f"Request took {duration:.2f}s")
        return response
```

### 2. Retry Rates

Monitor how often API requests need to be retried.

**What to Monitor:**
- Total number of retries per hour
- Retry success rate (retries that eventually succeed)
- Endpoints with highest retry rates

**Target Values:**
- Retry rate: < 5% of total requests
- Retry success rate: > 90%

**How to Monitor:**

```bash
# Check logs for retry patterns
grep "Retry" /var/log/allianceauth/wanderer.log | wc -l

# Count by endpoint
grep "POST.*retry" /var/log/allianceauth/wanderer.log | awk '{print $3}' | sort | uniq -c
```

### 3. Cache Hit Rates

Monitor cache effectiveness if caching is enabled.

**What to Monitor:**
- Cache hit ratio (hits / total requests)
- Cache miss ratio
- Cache size and eviction rate

**Target Values:**
- Hit rate: > 70% after warmup period
- Miss rate: < 30%

**How to Monitor:**

```python
# In Django shell
from django.core.cache import cache

# For Redis backend
cache._cache.info('stats')

# Or use custom cache wrapper
from wanderer.cache import WandererCache

# Add hit/miss tracking
class MonitoredCache(WandererCache):
    hits = 0
    misses = 0

    @classmethod
    def get_hit_rate(cls):
        total = cls.hits + cls.misses
        return cls.hits / total if total > 0 else 0
```

### 4. Error Rates

Track API and application errors.

**What to Monitor:**
- Total errors per hour
- Errors by type (timeout, 5xx, authentication, etc.)
- Error rate by endpoint

**Target Values:**
- Total error rate: < 1% of requests
- Authentication errors: 0
- Timeout errors: < 0.5%

**How to Monitor:**

```bash
# Total errors
grep "ERROR" /var/log/allianceauth/wanderer.log | wc -l

# By error type
grep "ERROR" /var/log/allianceauth/wanderer.log | awk '{print $5}' | sort | uniq -c

# Timeout errors specifically
grep "timed out" /var/log/allianceauth/wanderer.log | wc -l
```

### 5. Database Query Performance

Monitor database queries for the wanderer plugin.

**What to Monitor:**
- Number of queries per request
- Slow queries (> 100ms)
- N+1 query problems

**Target Values:**
- Queries per request: < 10
- Slow queries: < 1% of total
- No N+1 patterns

**How to Monitor:**

```python
# settings/local.py - Enable query logging
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['file'],
    'level': 'DEBUG',
}

# Or use Django Debug Toolbar in development
INSTALLED_APPS += ['debug_toolbar']
```

### 6. Celery Task Performance

Monitor async task execution for wanderer tasks.

**What to Monitor:**
- Task execution time
- Task failure rate
- Queue length
- Task retries

**Target Values:**
- Average task time: < 30 seconds
- Task failure rate: < 2%
- Queue length: < 50 tasks

**How to Monitor:**

```bash
# Using Celery Flower (recommended)
pip install flower
celery -A myauth flower

# Or check logs
grep "wanderer.tasks" /var/log/allianceauth/celery.log
```

## Logging Configuration

### Recommended Logging Setup

```python
# settings/local.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'wanderer_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/allianceauth/wanderer.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'wanderer_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/allianceauth/wanderer_debug.log',
            'maxBytes': 10485760,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'wanderer': {
            'handlers': ['wanderer_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'wanderer.http_client': {
            'handlers': ['wanderer_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'wanderer.cache': {
            'handlers': ['wanderer_debug'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Log Levels

**PRODUCTION:**
- wanderer: INFO
- wanderer.http_client: INFO
- wanderer.cache: INFO

**DEBUGGING:**
- wanderer: DEBUG
- wanderer.http_client: DEBUG
- wanderer.cache: DEBUG

### Important Log Messages

**INFO Level:**
- ACL creation
- User linking/unlinking
- Character additions/removals
- Cache invalidation
- Task execution

**WARNING Level:**
- Users without characters
- Retry attempts
- Rate limiting

**ERROR Level:**
- API authentication failures
- Timeouts
- Unexpected errors
- Task failures

## Performance Monitoring

### Django Debug Toolbar (Development)

Install and configure for development:

```python
# settings/local.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

INTERNAL_IPS = ['127.0.0.1']

# Show queries, cache, and timing panels
DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.timer.TimerPanel',
]
```

### Django Silk (Production Profiling)

For production performance profiling:

```bash
pip install django-silk
```

```python
# settings/local.py
INSTALLED_APPS += ['silk']
MIDDLEWARE.insert(0, 'silk.middleware.SilkyMiddleware')

SILKY_PYTHON_PROFILER = True
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
```

Access at: `https://your-auth.com/silk/`

### APM Tools

Consider integrating with Application Performance Monitoring tools:

**Sentry:**
```bash
pip install sentry-sdk
```

```python
# settings/local.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
)
```

**New Relic, DataDog, etc.:**
Follow their Django integration guides.

## Alert Configuration

### Critical Alerts

Configure alerts for critical issues:

1. **High Error Rate**
   - Condition: Error rate > 5% over 5 minutes
   - Action: Page on-call engineer

2. **Service Down**
   - Condition: Wanderer API unreachable
   - Action: Page on-call engineer

3. **Database Connection Failed**
   - Condition: Database connection errors
   - Action: Page on-call engineer

### Warning Alerts

Configure notifications for warning conditions:

1. **High Retry Rate**
   - Condition: Retry rate > 10% over 10 minutes
   - Action: Notify team channel

2. **Slow Responses**
   - Condition: 95th percentile > 5 seconds
   - Action: Notify team channel

3. **Cache Hit Rate Low**
   - Condition: Hit rate < 50% over 30 minutes
   - Action: Notify team channel

4. **Queue Backlog**
   - Condition: Celery queue > 100 tasks
   - Action: Notify team channel

### Example Alert Script

```python
#!/usr/bin/env python
"""
Alert script for wanderer monitoring.
Run via cron every 5 minutes.
"""

import subprocess
import sys

def check_error_rate():
    """Check if error rate is too high."""
    cmd = "grep -c ERROR /var/log/allianceauth/wanderer.log"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    error_count = int(result.stdout.decode().strip() or 0)

    if error_count > 50:  # More than 50 errors in log
        send_alert("High error rate detected", f"{error_count} errors found")

def check_service_health():
    """Check if service is responding."""
    from wanderer.models import WandererManagedMap

    try:
        # Try to query a map
        map = WandererManagedMap.objects.first()
        if map:
            # Try to get ACL members (will call API)
            members = map.get_character_ids_on_access_list()
    except Exception as e:
        send_alert("Service health check failed", str(e))

def send_alert(subject, message):
    """Send alert notification."""
    # Implement your notification method
    # - Email
    # - Slack
    # - PagerDuty
    # - etc.
    print(f"ALERT: {subject} - {message}")

if __name__ == "__main__":
    check_error_rate()
    check_service_health()
```

## Troubleshooting

### Common Issues

#### 1. High Response Times

**Symptoms:**
- Slow page loads
- Users complaining about lag
- High 95th percentile response times

**Diagnosis:**
```bash
# Check API response times in logs
grep "POST\|GET\|PUT\|DELETE" /var/log/allianceauth/wanderer_debug.log | grep "->

" | awk '{print $NF}' | sort -n

# Check database query times
grep "SELECT" /var/log/allianceauth/django.log | grep "slow"
```

**Solutions:**
1. Enable caching (see CACHE_CONFIG.md)
2. Increase cache timeouts
3. Check Wanderer server performance
4. Review database indexes
5. Optimize queries (check for N+1)

#### 2. Frequent Timeouts

**Symptoms:**
- Timeout errors in logs
- Operations failing intermittently

**Diagnosis:**
```bash
# Count timeout errors
grep "timed out" /var/log/allianceauth/wanderer.log | wc -l

# Check which operations timeout
grep "timed out" /var/log/allianceauth/wanderer.log | awk '{print $3}' | sort | uniq -c
```

**Solutions:**
1. Increase `WANDERER_API_TIMEOUT` setting
2. Check network latency to Wanderer
3. Verify Wanderer server health
4. Review operations for optimization

#### 3. Cache Issues

**Symptoms:**
- Low cache hit rates
- Stale data being served
- Excessive API calls

**Diagnosis:**
```python
# Check cache status
from django.core.cache import cache
print(cache._cache.info('stats'))  # For Redis

# Check cache keys
from wanderer.cache import WandererCache
# ... check specific keys
```

**Solutions:**
1. Verify Redis is running and accessible
2. Check cache timeout settings
3. Verify cache invalidation is working
4. Clear and rebuild cache

#### 4. Task Failures

**Symptoms:**
- Celery tasks failing
- Characters not being added to ACL
- Sync not working

**Diagnosis:**
```bash
# Check celery logs
tail -f /var/log/allianceauth/celery.log

# Check task status
celery -A myauth inspect active
celery -A myauth inspect reserved
```

**Solutions:**
1. Check task retry configuration
2. Verify Redis/RabbitMQ is running
3. Check for API authentication issues
4. Review task code for errors

## Best Practices

### 1. Regular Log Review

- Review logs weekly for patterns
- Set up log rotation to prevent disk space issues
- Archive important logs for compliance

### 2. Performance Baselines

- Establish performance baselines after deployment
- Monitor deviations from baseline
- Re-baseline after major changes

### 3. Gradual Rollouts

- Test changes in development first
- Deploy to staging before production
- Monitor metrics closely after deployment
- Have rollback plan ready

### 4. Documentation

- Document normal metric ranges
- Maintain runbook for common issues
- Keep changelog of configuration changes
- Document alert response procedures

### 5. Regular Maintenance

- Clear old logs monthly
- Review and update alert thresholds
- Update dependencies regularly
- Test backup and recovery procedures

## Resources

- [HTTP_CLIENT_CONFIG.md](HTTP_CLIENT_CONFIG.md) - HTTP client configuration
- [CACHE_CONFIG.md](CACHE_CONFIG.md) - Cache configuration
- [Django Logging Documentation](https://docs.djangoproject.com/en/stable/topics/logging/)
- [Celery Monitoring](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)
- [Alliance Auth Documentation](https://allianceauth.readthedocs.io/)
