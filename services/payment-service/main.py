from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os, time, random

app = FastAPI(title="Payment Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REQUEST_COUNT = Counter('payment_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('payment_request_latency_seconds', 'Latency')
PAYMENT_SUCCESS = Counter('payment_success_total', 'Successful payments')
PAYMENT_FAILED = Counter('payment_failed_total', 'Failed payments')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/paymentdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer)
    amount = Column(Float)
    status = Column(String, default="pending")
    method = Column(String, default="card")
    created_at = Column(DateTime, default=datetime.utcnow)

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    method: str = "card"

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
            print("Payment DB initialized")
            return
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "payment"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/payments")
def create_payment(payment: PaymentCreate, db=Depends(get_db)):
    start = time.time()
    success = random.random() > 0.1
    status = "completed" if success else "failed"
    db_payment = Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        method=payment.method,
        status=status
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    if success:
        PAYMENT_SUCCESS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/payments", status="200").inc()
    else:
        PAYMENT_FAILED.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/payments", status="402").inc()
    REQUEST_LATENCY.observe(time.time() - start)
    return db_payment

@app.get("/payments")
def get_payments(db=Depends(get_db)):
    return db.query(Payment).all()

@app.get("/payments/{payment_id}")
def get_payment(payment_id: int, db=Depends(get_db)):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    return p