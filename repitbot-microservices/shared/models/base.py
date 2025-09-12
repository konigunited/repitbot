# -*- coding: utf-8 -*-
"""
Base models and utilities for RepitBot microservices.
Provides common database model patterns and utilities.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field


# SQLAlchemy Base
Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                       onupdate=func.now(), nullable=False)


class BaseDBModel(Base):
    """Base database model with common patterns."""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    @declared_attr
    def __tablename__(cls):
        # Automatically generate table name from class name
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseDBModel':
        """Create model instance from dictionary."""
        return cls(**{
            key: value for key, value in data.items()
            if hasattr(cls, key)
        })


class AuditMixin(TimestampMixin):
    """Mixin to add audit fields to models."""
    
    created_by = Column(Integer, nullable=True)  # User ID who created
    updated_by = Column(Integer, nullable=True)  # User ID who last updated
    version = Column(Integer, default=1, nullable=False)  # Optimistic locking
    
    def update_audit_fields(self, user_id: Optional[int] = None):
        """Update audit fields before save."""
        self.updated_by = user_id
        self.version += 1


class SoftDeleteMixin:
    """Mixin to add soft delete functionality."""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    def soft_delete(self):
        """Mark record as deleted without actual removal."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


# Pydantic Base Models for API schemas
class BaseSchema(BaseModel):
    """Base Pydantic model for API schemas."""
    
    class Config:
        # Enable ORM mode for SQLAlchemy integration
        from_attributes = True
        # Allow population by field name or alias
        populate_by_name = True
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=10, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseSchema):
    """Standard paginated response format."""
    
    items: list = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    pages: int = Field(ge=0)
    
    @classmethod
    def create(cls, items: list, total: int, page: int, size: int) -> 'PaginatedResponse':
        """Create paginated response."""
        pages = (total + size - 1) // size  # Ceiling division
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )


class EventBase(BaseSchema):
    """Base event model for inter-service communication."""
    
    event_id: str = Field(description="Unique event identifier")
    event_type: str = Field(description="Type of event")
    service_name: str = Field(description="Service that generated the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    user_id: Optional[int] = Field(None, description="User associated with event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthCheckResponse(BaseSchema):
    """Standard health check response."""
    
    status: str = Field(description="Service status")
    service_name: str = Field(description="Name of the service")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class APIResponse(BaseSchema):
    """Standard API response wrapper."""
    
    success: bool = Field(default=True)
    message: Optional[str] = Field(None)
    data: Optional[Any] = Field(None)
    errors: Optional[list] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "Success") -> 'APIResponse':
        """Create successful response."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, message: str, errors: list = None) -> 'APIResponse':
        """Create error response."""
        return cls(success=False, message=message, errors=errors or [])


# Database utility functions
class DatabaseManager:
    """Database utilities for microservices."""
    
    @staticmethod
    def apply_pagination(query, pagination: PaginationParams):
        """Apply pagination to SQLAlchemy query."""
        return query.offset(pagination.offset).limit(pagination.size)
    
    @staticmethod
    def get_total_count(session: Session, model_class) -> int:
        """Get total count of records for a model."""
        return session.query(model_class).count()
    
    @staticmethod
    def create_paginated_response(
        session: Session,
        query,
        pagination: PaginationParams,
        model_class
    ) -> PaginatedResponse:
        """Create paginated response from query."""
        total = session.query(model_class).count()
        items = DatabaseManager.apply_pagination(query, pagination).all()
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size
        )


# TODO: Add more base utilities as needed:
# - BaseRepository pattern
# - Event sourcing base classes
# - Caching utilities
# - Validation utilities
# - Serialization utilities