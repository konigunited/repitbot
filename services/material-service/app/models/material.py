# -*- coding: utf-8 -*-
"""
Material Service Models
SQLAlchemy models for educational materials and file management
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Enum as SAEnum,
    Boolean, ForeignKey, Index, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class MaterialType(enum.Enum):
    """Material type enumeration"""
    TEXTBOOK = "textbook"
    WORKSHEET = "worksheet"
    EXERCISE = "exercise"
    REFERENCE = "reference"
    GAME = "game"
    VIDEO = "video"
    AUDIO = "audio"
    PRESENTATION = "presentation"
    OTHER = "other"


class FileType(enum.Enum):
    """File type enumeration"""
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    PPT = "ppt"
    PPTX = "pptx"
    TXT = "txt"
    RTF = "rtf"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    BMP = "bmp"
    SVG = "svg"
    MP3 = "mp3"
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WAV = "wav"
    ZIP = "zip"
    RAR = "rar"
    OTHER = "other"


class AccessLevel(enum.Enum):
    """Access level enumeration"""
    PUBLIC = "public"      # Available to all
    PRIVATE = "private"    # Only creator
    SHARED = "shared"      # Shared with specific users
    GRADE_SPECIFIC = "grade_specific"  # Available to specific grades


class MaterialCategory(Base):
    """Material category model"""
    __tablename__ = 'material_categories'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('material_categories.id'), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(50), nullable=True)  # Icon class or emoji
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Self-referential relationship for subcategories
    parent = relationship("MaterialCategory", remote_side=[id], back_populates="children")
    children = relationship("MaterialCategory", back_populates="parent", cascade="all, delete-orphan")
    
    # Relationship to materials
    materials = relationship("Material", back_populates="category", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_categories_parent', 'parent_id'),
        Index('idx_categories_active', 'is_active'),
    )


class Material(Base):
    """
    Material model - educational materials and resources
    Enhanced from existing Material model
    """
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)  # External link (optional)
    
    # Material properties
    material_type = Column(SAEnum(MaterialType), default=MaterialType.OTHER, nullable=False)
    grade = Column(Integer, nullable=False, default=5, index=True)  # Class grade 1-11
    subject = Column(String(100), nullable=True)  # Math, Russian, etc.
    topic = Column(String(200), nullable=True)   # Specific topic
    
    # Access control
    access_level = Column(SAEnum(AccessLevel), default=AccessLevel.PUBLIC, nullable=False)
    created_by_user_id = Column(Integer, nullable=True)  # Reference to User service
    
    # Metadata
    tags = Column(Text, nullable=True)  # JSON array of tags
    difficulty_level = Column(Integer, nullable=True)  # 1-5 scale
    estimated_time = Column(Integer, nullable=True)  # Minutes
    language = Column(String(10), default="ru", nullable=False)
    
    # Statistics
    view_count = Column(Integer, default=0, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    rating_sum = Column(Integer, default=0, nullable=False)
    rating_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    category_id = Column(Integer, ForeignKey('material_categories.id'), nullable=True)
    
    # Relationships
    category = relationship("MaterialCategory", back_populates="materials")
    files = relationship("MaterialFile", back_populates="material", cascade="all, delete-orphan")
    reviews = relationship("MaterialReview", back_populates="material", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_materials_grade_active', 'grade', 'is_active'),
        Index('idx_materials_type_grade', 'material_type', 'grade'),
        Index('idx_materials_category', 'category_id'),
        Index('idx_materials_created_by', 'created_by_user_id'),
        Index('idx_materials_featured', 'is_featured'),
    )
    
    @property
    def average_rating(self):
        """Calculate average rating"""
        if self.rating_count > 0:
            return round(self.rating_sum / self.rating_count, 1)
        return 0.0


class MaterialFile(Base):
    """Material file model - stores file information"""
    __tablename__ = 'material_files'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # File info
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=True)  # Public URL if available
    
    # File properties
    file_type = Column(SAEnum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    checksum = Column(String(64), nullable=True)   # SHA256 hash
    
    # File metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary file for material
    
    # Preview/thumbnail
    thumbnail_path = Column(String(500), nullable=True)
    preview_path = Column(String(500), nullable=True)
    has_preview = Column(Boolean, default=False, nullable=False)
    
    # Access control
    is_downloadable = Column(Boolean, default=True, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    upload_completed = Column(Boolean, default=False, nullable=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    uploaded_by_user_id = Column(Integer, nullable=True)  # Reference to User service
    
    # Relationships
    material = relationship("Material", back_populates="files")
    
    # Indexes
    __table_args__ = (
        Index('idx_material_files_material', 'material_id'),
        Index('idx_material_files_type', 'file_type'),
        Index('idx_material_files_active', 'is_active'),
    )


class MaterialReview(Base):
    """Material review/rating model"""
    __tablename__ = 'material_reviews'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Review metadata
    is_anonymous = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Verified user
    helpful_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_approved = Column(Boolean, default=True, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    user_id = Column(Integer, nullable=False)  # Reference to User service
    
    # Relationships
    material = relationship("Material", back_populates="reviews")
    
    # Indexes
    __table_args__ = (
        Index('idx_material_reviews_material', 'material_id'),
        Index('idx_material_reviews_user', 'user_id'),
        Index('idx_material_reviews_rating', 'rating'),
        Index('idx_material_reviews_approved', 'is_approved'),
    )


class MaterialAccess(Base):
    """Material access log for analytics"""
    __tablename__ = 'material_access'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Access details
    access_type = Column(String(20), nullable=False)  # view, download, share
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    referer = Column(String(500), nullable=True)
    
    # Timestamps
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign keys
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    file_id = Column(Integer, ForeignKey('material_files.id'), nullable=True)
    user_id = Column(Integer, nullable=True)  # Reference to User service (if logged in)
    
    # Indexes
    __table_args__ = (
        Index('idx_material_access_material', 'material_id'),
        Index('idx_material_access_user', 'user_id'),
        Index('idx_material_access_date', 'accessed_at'),
        Index('idx_material_access_type', 'access_type'),
    )