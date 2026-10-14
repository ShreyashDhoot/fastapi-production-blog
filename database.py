from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase , sessionmaker 

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

# fast api allows multiple threads but SQL alchemy does not which is why we disabled check same thread 
# not necessary for postgres or mysql 
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread":False},
)

#to control when changes are commited , fastapi standard 
SessionLocal = sessionmaker(autocommit = False, autoflush = False , bind = engine)

class Base(DeclarativeBase):
    pass 

# dependency function provides scessions to our routes 
#makes the scession work as a context manager 
def get_db():
    with SessionLocal() as db:
        yield db
