import os
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Use environment variables for sensitive information
POSTGRES_USER = os.getenv("POSTGRES_USER", "your_username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "your_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "your_database")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create asynchronous engine
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Create asynchronous sessionmaker
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()

# Configure logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous generator that yields an AsyncSession and ensures it is properly closed after use.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logging.error(f"Session rollback because of exception: {e}")
            raise
        finally:
            await session.close()
