from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# | Character | Encoded Form |
# | --------- | ------------ |
# | `$`       | `%24`        |
# | `%`       | `%25`        |
# | `@`       | `%40`        |

# ✅ Use URL-encoded password
DATABASE_URL = "mysql+pymysql://usmdev:18F440%240h%25Bb@testing-usm.cskrfn8se5q9.ap-south-1.rds.amazonaws.com/amoeba-interview"
# DATABASE_URL = "mysql+pymysql://root@192.168.1.140/amoeba-interview?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    connect_args={"charset": "utf8mb4"},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
