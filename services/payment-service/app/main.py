# -*- coding: utf-8 -*-
"""
Payment Service - FastAPI Application
Handles payment processing, balance management, and financial operations
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from .database.connection import init_db, get_db
from .api.v1.payments import router as payments_router
from .events.payment_events import PaymentEventHandler
from .core.config import settings


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global event handler
event_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global event_handler
    
    # Startup
    logger.info("Starting Payment Service...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize event handler
    event_handler = PaymentEventHandler()
    await event_handler.start()
    logger.info("Event handler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Payment Service...")
    if event_handler:
        await event_handler.stop()
    logger.info("Payment Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Payment Service",
    description="Microservice for payment processing and balance management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(payments_router, prefix="/api/v1", tags=["payments"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "payment-service",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Payment Service",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )