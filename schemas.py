from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AddressIn(BaseModel):
    label: str = "Home"
    address_text: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_default: bool = False

class RestaurantIn(BaseModel):
    name: str
    address: str
    cuisine: Optional[str] = None
    image_url: Optional[str] = None

class MenuItemIn(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float = Field(gt=0)
    is_veg: bool = True
    is_available: bool = True
    image_url: Optional[str] = None

class CartIn(BaseModel):
    item_id: int
    quantity: int = Field(ge=1, le=50)
    customization: Optional[str] = None

class CheckoutIn(BaseModel):
    address_id: int
    payment_method: str = "COD"
    promo_code: Optional[str] = None
    tip: float = Field(default=0, ge=0)

class DecisionIn(BaseModel):
    decision: str
    preparation_minutes: Optional[int] = None

class StatusIn(BaseModel):
    status: str

class AvailabilityIn(BaseModel):
    availability: str

class DeliveryAssignIn(BaseModel):
    partner_id: int

class LocationIn(BaseModel):
    location: str

class ReviewIn(BaseModel):
    food_rating: int = Field(ge=1, le=5)
    delivery_rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

class TicketIn(BaseModel):
    order_id: Optional[int] = None
    subject: str
