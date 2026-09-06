# Day 16 — Rate Limiting

## Goal

Implement rate limiting to prevent excessive job submissions from overwhelming the TaskScale AI system.

Rate limiting is part of Phase 5 — Advanced Distributed Systems.

## Implementation

Redis is used to maintain a request counter.

Rate limit:

- Maximum requests: 5
- Time window: 60 seconds

Redis key:

taskscale:rate_limit:default-client

## Request Flow

Client
↓
POST /jobs
↓
Rate Limiter
↓
Redis Counter
↓
Allowed
↓
PostgreSQL
↓
Redis Stream
↓
Worker

If the limit is exceeded:

Client
↓
POST /jobs
↓
Rate Limiter
↓
HTTP 429 Too Many Requests

## Redis Counter

The rate limiter creates a Redis key for the client.

Example:

taskscale:rate_limit:default-client

The counter increases for each accepted request.

The key expires automatically after 60 seconds.

## Testing

The rate limit was configured for 5 requests per 60 seconds.

The first five requests were accepted.

The sixth request was rejected.

Response:

HTTP 429 Too Many Requests

Response body:

{
    "detail": "Rate limit exceeded. Try again later."
}

## Redis Verification

Command:

GET taskscale:rate_limit:default-client

Result:

"5"

This confirms that the Redis counter reached the configured limit.

## Result

Rate limiting is working correctly.

The API accepts up to 5 job submissions within the configured 60-second window and rejects additional requests with HTTP 429.

## Engineering Lesson

Redis can be used as a fast distributed counter for controlling request rates.

Rate limiting helps protect backend resources such as:

- FastAPI
- PostgreSQL
- Redis
- Workers

It is an important mechanism for controlling system overload.

## Current Limitation

The current implementation uses:

default-client

as the client identifier.

This is intentional for the first implementation and testing phase. A production implementation could use an authenticated user ID, API key, IP address, or another appropriate client identity.

## Phase 5 Progress

- Priority Scheduling — COMPLETE
- Rate Limiting — COMPLETE
- Backpressure — NEXT
- Distributed Locking
- Leader Election
- Job Dependencies
- DAG-based Workflows