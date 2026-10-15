from sqlalchemy.ext.asyncio import AsyncSession , async_sessionmaker , create_async_engine
from sqlalchemy.orm import DeclarativeBase 

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

# fast api allows multiple threads but SQL alchemy does not which is why we disabled check same thread 
# not necessary for postgres or mysql 
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread":False},
)

#to control when changes are commited , fastapi standard 
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession,expire_on_commit=False)

class Base(DeclarativeBase):
    pass 

# dependency function provides scessions to our routes 
#makes the scession work as a context manager 
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
