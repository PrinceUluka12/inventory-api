from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/products", tags=["stock"])

@router.post("/{id}/stock-movements", response_model=schemas.StockMovementOut)
def add_stock_movement(id: int, movement: schemas.StockMovementCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db_movement = models.StockMovement(product_id=id, **movement.dict())
    db.add(db_movement)
    db.commit()
    db.refresh(db_movement)
    return db_movement

@router.get("/{id}/stock-movements", response_model=list[schemas.StockMovementOut])
def get_stock_movements(id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db.query(models.StockMovement).filter(models.StockMovement.product_id == id).all()