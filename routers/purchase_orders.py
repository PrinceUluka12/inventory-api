from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth import get_current_user
import models, schemas
from datetime import datetime

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

@router.post("/", response_model=schemas.PurchaseOrderOut)
def create_purchase_order(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == po.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db_po = models.PurchaseOrder(
        supplier_id=po.supplier_id,
        expected_delivery_date=po.expected_delivery_date,
        notes=po.notes,
        created_by=current_user.id
    )
    for item in po.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        db_po.items.append(models.PurchaseOrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        ))
    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    return db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items)).filter(models.PurchaseOrder.id == db_po.id).first()

@router.get("/", response_model=list[schemas.PurchaseOrderOut])
def get_purchase_orders(supplier_id: int = Query(default=None), status: str = Query(default=None), db: Session = Depends(get_db)):
    q = db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items))
    if supplier_id:
        q = q.filter(models.PurchaseOrder.supplier_id == supplier_id)
    if status and status in [s.value for s in models.PurchaseOrderStatus]:
        q = q.filter(models.PurchaseOrder.status == models.PurchaseOrderStatus(status))
    return q.all()

@router.get("/{id}", response_model=schemas.PurchaseOrderOut)
def get_purchase_order(id: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items)).filter(models.PurchaseOrder.id == id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po

@router.put("/{id}", response_model=schemas.PurchaseOrderOut)
def update_purchase_order(id: int, po_update: schemas.PurchaseOrderUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items)).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po_update.status is not None:
        if db_po.status in [models.PurchaseOrderStatus.RECEIVED, models.PurchaseOrderStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Cannot change status from terminal state")
        if po_update.status == models.PurchaseOrderStatus.RECEIVED:
            for item in db_po.items:
                movement = models.StockMovement(
                    product_id=item.product_id,
                    movement_type=models.MovementType.IN,
                    quantity=item.quantity,
                    notes=f"Received from PO #{db_po.id}"
                )
                db.add(movement)
            db_po.received_at = datetime.utcnow()
        db_po.status = po_update.status
    if po_update.expected_delivery_date is not None:
        db_po.expected_delivery_date = po_update.expected_delivery_date
    if po_update.notes is not None:
        db_po.notes = po_update.notes
    db.commit()
    db.refresh(db_po)
    return db.query(models.PurchaseOrder).options(joinedload(models.PurchaseOrder.items)).filter(models.PurchaseOrder.id == db_po.id).first()

@router.delete("/{id}")
def delete_purchase_order(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status == models.PurchaseOrderStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Cannot delete a received purchase order")
    db.delete(db_po)
    db.commit()
    return {"message": "Purchase order deleted"}
