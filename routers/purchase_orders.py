from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

@router.get("/", response_model=list[schemas.PurchaseOrderOut])
def get_purchase_orders(db: Session = Depends(get_db)):
    return db.query(models.PurchaseOrder).all()

@router.get("/{id}", response_model=schemas.PurchaseOrderOut)
def get_purchase_order(id: int, db: Session = Depends(get_db)):
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po

@router.post("/", response_model=schemas.PurchaseOrderOut)
def create_purchase_order(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == po.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier not found")
    for item in po.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
    db_po = models.PurchaseOrder(
        supplier_id=po.supplier_id,
        expected_date=po.expected_date,
        notes=po.notes,
        created_by=current_user.id
    )
    db.add(db_po)
    db.flush()
    for item in po.items:
        db_item = models.PurchaseOrderItem(
            po_id=db_po.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            unit_price=item.unit_price
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_po)
    return db_po

@router.put("/{id}", response_model=schemas.PurchaseOrderOut)
def update_purchase_order(id: int, po: schemas.PurchaseOrderUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only update DRAFT purchase orders")
    for key, value in po.dict(exclude_unset=True).items():
        setattr(db_po, key, value)
    db.commit()
    db.refresh(db_po)
    return db_po

@router.delete("/{id}")
def delete_purchase_order(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete DRAFT purchase orders")
    db.delete(db_po)
    db.commit()
    return {"message": "Purchase order deleted"}

@router.post("/{id}/submit", response_model=schemas.PurchaseOrderOut)
def submit_purchase_order(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only submit DRAFT purchase orders")
    if not db_po.items:
        raise HTTPException(status_code=400, detail="Cannot submit purchase order with no items")
    db_po.status = models.POStatus.SUBMITTED
    db.commit()
    db.refresh(db_po)
    return db_po

@router.post("/{id}/receive", response_model=schemas.PurchaseOrderOut)
def receive_purchase_order(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Can only receive SUBMITTED purchase orders")
    for item in db_po.items:
        stock_movement = models.StockMovement(
            product_id=item.product_id,
            movement_type=models.MovementType.IN,
            quantity=item.quantity_ordered,
            notes=f"Received from PO #{db_po.id}"
        )
        db.add(stock_movement)
    db_po.status = models.POStatus.RECEIVED
    db.commit()
    db.refresh(db_po)
    return db_po

@router.post("/{id}/cancel", response_model=schemas.PurchaseOrderOut)
def cancel_purchase_order(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status not in [models.POStatus.DRAFT, models.POStatus.SUBMITTED]:
        raise HTTPException(status_code=400, detail="Can only cancel DRAFT or SUBMITTED purchase orders")
    db_po.status = models.POStatus.CANCELLED
    db.commit()
    db.refresh(db_po)
    return db_po

@router.post("/{id}/items", response_model=schemas.PurchaseOrderItemOut)
def add_purchase_order_item(id: int, item: schemas.PurchaseOrderItemCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only add items to DRAFT purchase orders")
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=400, detail="Product not found")
    db_item = models.PurchaseOrderItem(
        po_id=id,
        product_id=item.product_id,
        quantity_ordered=item.quantity_ordered,
        unit_price=item.unit_price
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{id}/items/{item_id}", response_model=schemas.PurchaseOrderItemOut)
def update_purchase_order_item(id: int, item_id: int, item: schemas.PurchaseOrderItemUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only update items in DRAFT purchase orders")
    db_item = db.query(models.PurchaseOrderItem).filter(
        models.PurchaseOrderItem.id == item_id,
        models.PurchaseOrderItem.po_id == id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Purchase order item not found")
    for key, value in item.dict(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{id}/items/{item_id}")
def delete_purchase_order_item(id: int, item_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if db_po.status != models.POStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete items from DRAFT purchase orders")
    db_item = db.query(models.PurchaseOrderItem).filter(
        models.PurchaseOrderItem.id == item_id,
        models.PurchaseOrderItem.po_id == id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Purchase order item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Purchase order item deleted"}
