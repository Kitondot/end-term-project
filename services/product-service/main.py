from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
import os, time

app = FastAPI(title="Product Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

REQUEST_COUNT = Counter('product_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('product_request_latency_seconds', 'Latency')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/productdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=100)

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int = 100

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
            db = SessionLocal()
            if db.query(Product).count() == 0:
                sample_products = [
                    Product(name="Laptop", description="High-performance laptop", price=999.99, stock=50),
                    Product(name="Mouse", description="Wireless mouse", price=29.99, stock=200),
                    Product(name="Keyboard", description="Mechanical keyboard", price=79.99, stock=150),
                    Product(name="Monitor", description="4K monitor", price=399.99, stock=30),
                ]
                db.add_all(sample_products)
                db.commit()
            db.close()
            print("Product DB initialized")
            return
        except Exception as e:
            print(f"DB init attempt {i+1} failed: {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "healthy", "service": "product"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/products")
def get_products(db=Depends(get_db)):
    start = time.time()
    products = db.query(Product).all()
    REQUEST_COUNT.labels(method="GET", endpoint="/products", status="200").inc()
    REQUEST_LATENCY.observe(time.time() - start)
    return products

@app.get("/products/{product_id}")
def get_product(product_id: int, db=Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        REQUEST_COUNT.labels(method="GET", endpoint="/products/id", status="404").inc()
        raise HTTPException(status_code=404, detail="Product not found")
    REQUEST_COUNT.labels(method="GET", endpoint="/products/id", status="200").inc()
    return product

@app.post("/products")
def create_product(product: ProductCreate, db=Depends(get_db)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    REQUEST_COUNT.labels(method="POST", endpoint="/products", status="200").inc()
    return db_product