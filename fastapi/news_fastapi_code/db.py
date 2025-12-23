# db.py
from sqlalchemy import create_engine
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

# 환경변수 누락 체크
missing = [
    k for k, v in {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_NAME": DB_NAME,
    }.items() if not v
]
if missing:
    raise RuntimeError(f"Missing DB environment variables: {missing}")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
)
