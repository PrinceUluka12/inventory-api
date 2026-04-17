from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import MovementType

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    class Config:
        from_attributes = True

class SupplierCreate(BaseModel):
    name: str
    contact_email: str
    phone: Optional[str] = None
    address: Optional[str] = None

class SupplierOut(BaseModel):
    id: int
    name: str
    contact_email: str
    phone: Optional[str]
    address: Optional[str]
    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    category_id: int
    supplier_id: int
    unit_price: float

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sku: str
    category_id: int
    supplier_id: int
    unit_price: float
    created_at: datetime
    class Config:
        from_attributes = True

class ProductWithStock(ProductOut):
    current_stock: int

class StockMovementCreate(BaseModel):
    movement_type: MovementType
    quantity: int
    notes: Optional[str] = None

class StockMovementOut(BaseModel):
    id: int
    product_id: int
    movement_type: MovementType
    quantity: int
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True