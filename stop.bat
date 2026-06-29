@echo off

taskkill /FI "WINDOWTITLE eq FastAPI" /F
taskkill /FI "WINDOWTITLE eq Celery" /F