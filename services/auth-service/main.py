from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext
from jose import jwt
import os
import time

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Метрики Prometheus
REQUEST_COUNT = Counter('auth_requests_total', 'Total requests to auth service', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('auth_request_latency_seconds', 'Request latency')

# База данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/authdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey123")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    retries = 5
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database initialized successfully")
            return
        except Exception as e:
            print(f"DB init attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "healthy", "service": "auth"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/register")
def register(req: RegisterRequest, db=Depends(get_db)):
    start = time.time()
    try:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            REQUEST_COUNT.labels(method="POST", endpoint="/register", status="400").inc()
            raise HTTPException(status_code=400, detail="User already exists")
        hashed = pwd_context.hash(req.password)
        user = User(username=req.username, hashed_password=hashed)
        db.add(user)
        db.commit()
        REQUEST_COUNT.labels(method="POST", endpoint="/register", status="200").inc()
        return {"message": "User registered successfully"}
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/login")
def login(req: LoginRequest, db=Depends(get_db)):
    start = time.time()
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not pwd_context.verify(req.password, user.hashed_password):
            REQUEST_COUNT.labels(method="POST", endpoint="/login", status="401").inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = jwt.encode({"sub": user.username, "id": user.id}, SECRET_KEY, algorithm=ALGORITHM)
        REQUEST_COUNT.labels(method="POST", endpoint="/login", status="200").inc()
        return {"access_token": token, "token_type": "bearer"}
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/verify")
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "username": payload.get("sub")}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")