import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    connect_args={"command_timeout": settings.db_command_timeout},
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            if session.dirty or session.new or session.deleted:
                logger.debug(
                    "Auto-committing session: dirty=%d new=%d deleted=%d",
                    len(session.dirty), len(session.new), len(session.deleted),
                )
                await session.commit()
        except Exception:
            await session.rollback()
            raise
