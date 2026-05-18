from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os, time

app = FastAPI(title="Order Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REQUEST_COUNT = Counter('order_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('order_request_latency_seconds', 'Latency')
ORDER_ERRORS = Counter('order_errors_total', 'Total order errors')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/orderdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    total_price: float

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
            print("Order DB initialized")
            return
        except Exception as e:
            print(f"DB init attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db.close()
        return {"status": "healthy", "service": "order"}
    except Exception as e:
        ORDER_ERRORS.inc()
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/orders")
def get_orders(db=Depends(get_db)):
    start = time.time()
    orders = db.query(Order).all()
    REQUEST_COUNT.labels(method="GET", endpoint="/orders", status="200").inc()
    REQUEST_LATENCY.observe(time.time() - start)
    return orders

@app.post("/orders")
def create_order(order: OrderCreate, db=Depends(get_db)):
    start = time.time()
    try:
        db_order = Order(**order.dict())
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="200").inc()
        return db_order
    except Exception as e:
        ORDER_ERRORS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/orders", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/orders/{order_id}")
def get_order(order_id: int, db=Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order