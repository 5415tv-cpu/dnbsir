#!/bin/bash
pkill -f "python.*uvicorn" || true
pkill -f "python.*main.py" || true
sleep 2
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
echo $! > uvicorn.pid
