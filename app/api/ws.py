import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis_client import get_async_redis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/inference/{sample_unit_id}")
async def inference_status_ws(
    websocket: WebSocket,
    sample_unit_id: UUID,
):
    await websocket.accept()

    redis = await get_async_redis()
    pubsub = redis.pubsub()
    channel = f"inference:{sample_unit_id}"

    await pubsub.subscribe(channel)

    # Send immediate acknowledgement so frontend knows it's connected
    await websocket.send_json(
        {"status": "processing", "step": "started", "detail": "Connecting..."}
    )

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            await websocket.send_json(data)

            if data.get("status") in ("done", "failed"):
                break

    except WebSocketDisconnect:
        logger.info(f"WS client disconnected for {sample_unit_id}")
    except Exception:
        logger.exception(f"WS error for {sample_unit_id}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.aclose()
        try:
            await websocket.close()
        except Exception:
            pass
