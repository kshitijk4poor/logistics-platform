import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Use environment variables for sensitive information
POSTGRES_USER = os.getenv("POSTGRES_USER", "your_username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "your_database")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# PgBouncer connection string
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:6432/{POSTGRES_DB}"

# Create asynchronous engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,
)

# Create asynchronous sessionmaker
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()

# Configure logging
logging.basicConfig()
