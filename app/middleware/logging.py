"""Structured logging middleware with Request-ID and Query Timing."""

import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("finance_api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '{"time": "%(asctime)s", "level": "%(levelname)s", "request_id": "%(request_id)s", "message": "%(message)s"}'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        
        # Inject request_id into state so routes can log it if needed
        request.state.request_id = request_id
        
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Only log slow requests > 1000ms or log everything
        extra = {"request_id": request_id}
        log_msg = f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s"
        
        if process_time > 1.0:
            logger.warning(f"SLOW QUERY: {log_msg}", extra=extra)
        else:
            logger.info(log_msg, extra=extra)
            
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response
