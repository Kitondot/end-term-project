from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os, time

app = FastAPI(title="User Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REQUEST_COUNT = Counter('user_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('user_request_latency_seconds', 'Latency')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/userdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    for i in range(5):
        try:
            Base.metadata.create_all(bind=engine)
            print("User DB initialized")
            return
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "user"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/users")
def get_users(db=Depends(get_db)):
    users = db.query(UserProfile).all()
    REQUEST_COUNT.labels(method="GET", endpoint="/users", status="200").inc()
    return users

@app.post("/users")
def create_user(user: UserCreate, db=Depends(get_db)):
    existing = db.query(UserProfile).filter(UserProfile.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    db_user = UserProfile(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    REQUEST_COUNT.labels(method="POST", endpoint="/users", status="200").inc()
    return db_user

@app.get("/users/{user_id}")
def get_user(user_id: int, db=Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user