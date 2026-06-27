sudo service redis-server stop
pkill -f "uvicorn"
pkill -f "celery"