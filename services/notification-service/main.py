from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os, time

app = FastAPI(title="Notification Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

NOTIFICATIONS_SENT = Counter('notifications_sent_total', 'Total notifications sent', ['type'])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/notificationdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String)
    type = Column(String)
    message = Column(String)
    status = Column(String, default="sent")
    created_at = Column(DateTime, default=datetime.utcnow)

class NotificationCreate(BaseModel):
    recipient: str
    type: str = "email"
    message: str

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
            print("Notification DB initialized")
            return
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "notification"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/notifications")
def send_notification(notif: NotificationCreate, db=Depends(get_db)):
    db_notif = Notification(**notif.dict())
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    NOTIFICATIONS_SENT.labels(type=notif.type).inc()
    print(f"[NOTIFICATION] To: {notif.recipient} | Type: {notif.type} | Msg: {notif.message}")
    return {"id": db_notif.id, "status": "sent", "recipient": notif.recipient}

@app.get("/notifications")
def get_notifications(db=Depends(get_db)):
    return db.query(Notification).all()