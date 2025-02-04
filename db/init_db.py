import logging

from app.models import Base
from sqlalchemy_utils import create_database, database_exists

from .database import SQLALCHEMY_DATABASE_URL, engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():

    try:
        if not database_exists(SQLALCHEMY_DATABASE_URL):
            create_database(SQLALCHEMY_DATABASE_URL)
            logger.info("Database created.")

        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"An error occurred while initializing the database: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())
