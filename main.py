from server.webhook_app import app

# This entry point is required for the Docker container CMD ["uvicorn", "main:app", ...]
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
