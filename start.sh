#!/bin/bsh

chmod +x start.sh

if ! pgrep -x "redis-server" > /dev/null; then
   echo "Starting Redis..."
   sudo service redis-server start
else 
   echo "Redis already running..."   

# Terminal 2 — FastAPI
echo "Starting FastAPI..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 — Celery worker
echo "Celery worker"
celery -A app.core.celery_app worker --loglevel=info --concurrency=2
# --concurrency=2 means 2 worker processes, each with its own model copy
# keep this low — each process loads YOLO into RAM/VRAM

echo "All services started."
wait