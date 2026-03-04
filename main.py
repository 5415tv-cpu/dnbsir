from server.webhook_app import app

# This entry point is required for the Docker container CMD ["uvicorn", "main:app", ...]
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
