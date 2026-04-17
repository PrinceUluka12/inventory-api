from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

@router.get("/", response_model=list[schemas.SupplierOut])
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()

@router.get("/{id}", response_model=schemas.SupplierOut)
def get_supplier(id: int, db: Session = Depends(get_db)):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.post("/", response_model=schemas.SupplierOut)
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(models.Supplier).filter(models.Supplier.name == supplier.name).first():
        raise HTTPException(status_code=400, detail="Supplier already exists")
    db_supplier = models.Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.put("/{id}", response_model=schemas.SupplierOut)
def update_supplier(id: int, supplier: schemas.SupplierCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for key, value in supplier.dict().items():
        setattr(db_supplier, key, value)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.delete("/{id}")
def delete_supplier(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(db_supplier)
    db.commit()
    return {"message": "Supplier deleted"}