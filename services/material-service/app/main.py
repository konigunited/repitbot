# -*- coding: utf-8 -*-
"""
Material Service - FastAPI Application
Handles educational materials library and file management
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging
import os

from .database.connection import init_db, get_db
from .api.v1.materials import router as materials_router
from .events.material_events import MaterialEventHandler
from .core.config import settings
from .storage.file_storage import FileStorageManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
event_handler = None
file_storage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global event_handler, file_storage
    
    # Startup
    logger.info("Starting Material Service...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize file storage
    file_storage = FileStorageManager()
    await file_storage.initialize()
    logger.info("File storage initialized")
    
    # Initialize event handler
    event_handler = MaterialEventHandler()
    await event_handler.start()
    logger.info("Event handler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Material Service...")
    if event_handler:
        await event_handler.stop()
    if file_storage:
        await file_storage.cleanup()
    logger.info("Material Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Material Service",
    description="Microservice for educational materials library and file management",
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

# Mount static files for material downloads
if not os.path.exists("./uploads"):
    os.makedirs("./uploads")
app.mount("/files", StaticFiles(directory="./uploads"), name="files")

# Include routers
app.include_router(materials_router, prefix="/api/v1", tags=["materials"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "material-service",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Material Service",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )