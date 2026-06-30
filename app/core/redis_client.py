import redis
from redis.asyncio import Redis as AsyncRedis

# Sync — used by Celery worker to publish
sync_redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Async — used by FastAPI WebSocket to subscribe
async def get_async_redis() -> AsyncRedis:
    return AsyncRedis(host="localhost", port=6379, db=0, decode_responses=True)