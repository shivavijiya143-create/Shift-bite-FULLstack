from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    phone = Column(String(25), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), default="customer", nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Address(Base):
    __tablename__ = "addresses"
    address_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    label = Column(String(50), default="Home")
    address_text = Column(Text, nullable=False)
    latitude = Column(String(40))
    longitude = Column(String(40))
    is_default = Column(Boolean, default=False)

class Restaurant(Base):
    __tablename__ = "restaurants"
    restaurant_id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(160), nullable=False)
    address = Column(Text, nullable=False)
    cuisine = Column(String(100))
    rating = Column(Numeric(2,1), default=0)
    status = Column(String(30), default="pending")
    is_open = Column(Boolean, default=True)
    image_url = Column(String(500))

class MenuItem(Base):
    __tablename__ = "menu_items"
    item_id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id"), nullable=False)
    name = Column(String(160), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price = Column(Numeric(10,2), nullable=False)
    is_veg = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    image_url = Column(String(500))

class CartItem(Base):
    __tablename__ = "cart_items"
    cart_item_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.item_id"), nullable=False)
    quantity = Column(Integer, default=1)
    customization = Column(Text)

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id"), nullable=False)
    total_amount = Column(Numeric(10,2), nullable=False)
    status = Column(String(30), default="placed")
    delivery_address = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrderItem(Base):
    __tablename__ = "order_items"
    order_item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    item_id = Column(Integer, ForeignKey("menu_items.item_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10,2), nullable=False)
    customization = Column(Text)

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    method = Column(String(30), nullable=False)
    amount = Column(Numeric(10,2), nullable=False)
    status = Column(String(30), default="pending")
    transaction_ref = Column(String(180))
    paid_at = Column(DateTime(timezone=True))

class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"
    partner_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    availability = Column(String(20), default="offline")
    vehicle = Column(String(80))
    current_location = Column(String(160))

class Delivery(Base):
    __tablename__ = "deliveries"
    delivery_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    partner_id = Column(Integer, ForeignKey("delivery_partners.partner_id"))
    status = Column(String(30), default="assigned")
    current_location = Column(String(160))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))

class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.restaurant_id"), nullable=False)
    food_rating = Column(Integer, nullable=False)
    delivery_rating = Column(Integer, nullable=False)
    comment = Column(Text)

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    ticket_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"))
    subject = Column(String(180), nullable=False)
    status = Column(String(30), default="open")
    resolution = Column(Text)

class Promotion(Base):
    __tablename__ = "promotions"
    promotion_id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    discount_type = Column(String(20), default="percent")
    discount_value = Column(Numeric(10,2), nullable=False)
    usage_limit = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)

class Notification(Base):
    __tablename__ = "notifications"
    notification_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    channel = Column(String(20), default="in_app")
    message = Column(Text, nullable=False)
    status = Column(String(20), default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
