"""
CF Credential Service 入口
"""

import logging
import os
import uvicorn

from src.api import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

PORT = int(os.environ.get("PORT", 20001))

if __name__ == "__main__":
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
    )
