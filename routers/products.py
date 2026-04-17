from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/products", tags=["products"])

def get_stock_level(product_id: int, db: Session) -> int:
    movements = db.query(models.StockMovement).filter(
        models.StockMovement.product_id == product_id
    ).all()
    total = 0
    for m in movements:
        if m.movement_type == models.MovementType.IN:
            total += m.quantity
        else:
            total -= m.quantity
    return total

@router.get("/", response_model=list[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@router.get("/low-stock", response_model=list[schemas.ProductWithStock])
def get_low_stock(threshold: int = Query(default=10), db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    result = []
    for p in products:
        stock = get_stock_level(p.id, db)
        if stock <= threshold:
            result.append({**p.__dict__, "current_stock": stock})
    return result

@router.get("/{id}", response_model=schemas.ProductOut)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{id}/stock", response_model=dict)
def get_product_stock(id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product_id": id, "current_stock": get_stock_level(id, db)}

@router.post("/", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(models.Product).filter(models.Product.sku == product.sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/{id}", response_model=schemas.ProductOut)
def update_product(id: int, product: schemas.ProductCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in product.dict().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{id}")
def delete_product(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_product = db.query(models.Product).filter(models.Product.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted"}