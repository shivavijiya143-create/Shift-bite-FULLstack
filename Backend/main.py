from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from .database import Base, engine, get_db
from . import models as m, schemas as s
from .security import hash_password, verify_password, create_token, current_user, allow

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ShiftBite API", version="2.0.0",
              description="Interconnected food delivery platform with four user portals.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
V1 = "/api/v1"
ROLES = ("admin", "customer", "restaurant_owner", "delivery_partner")


def notify(db, user_id, message):
    db.add(m.Notification(user_id=user_id, message=message,
                          channel="in_app", status="queued"))


def commit_changes(db):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_restaurant(db, user_id):
    return db.query(m.Restaurant).filter_by(owner_id=user_id).first()


def get_partner(db, user_id):
    return db.query(m.DeliveryPartner).filter_by(user_id=user_id).first()


def restaurant_order(db, order_id, user_id):
    restaurant = get_restaurant(db, user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant profile not found")
    order = db.query(m.Order).filter_by(
        order_id=order_id, restaurant_id=restaurant.restaurant_id
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


def checkout_summary(data, user, db):
    address = db.query(m.Address).filter_by(
        address_id=data.address_id, user_id=user.user_id
    ).first()
    if not address:
        raise HTTPException(400, "Select a valid saved address")

    cart = db.query(m.CartItem, m.MenuItem).join(
        m.MenuItem, m.CartItem.item_id == m.MenuItem.item_id
    ).filter(m.CartItem.user_id == user.user_id).all()
    if not cart:
        raise HTTPException(400, "Your cart is empty")

    restaurant_ids = {item.restaurant_id for cart_item, item in cart}
    if len(restaurant_ids) != 1:
        raise HTTPException(400, "Please order from one restaurant at a time")

    for cart_item, item in cart:
        restaurant = db.query(m.Restaurant).filter_by(
            restaurant_id=item.restaurant_id, status="approved", is_open=True
        ).first()
        if not item.is_available or not restaurant:
            raise HTTPException(400, f"{item.name} is currently unavailable")

    subtotal = sum(
        (Decimal(str(item.price)) * cart_item.quantity
         for cart_item, item in cart), Decimal("0.00")
    )
    delivery = Decimal("30.00")
    packaging = Decimal("10.00")
    tax = (subtotal * Decimal("0.05")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    discount = Decimal("0.00")

    if data.promo_code:
        promo = db.query(m.Promotion).filter(
            func.upper(m.Promotion.code) == data.promo_code.upper(),
            m.Promotion.is_active == True
        ).first()
        if promo:
            if promo.discount_type == "percent":
                discount = subtotal * promo.discount_value / 100
            else:
                discount = Decimal(str(promo.discount_value))
            discount = min(discount, subtotal)

    tip = Decimal(str(data.tip))
    total = max(Decimal("0.00"), subtotal + delivery + packaging + tax + tip - discount)
    return {
        "address": address, "cart": cart, "restaurant_id": next(iter(restaurant_ids)),
        "subtotal": subtotal, "delivery": delivery, "packaging": packaging,
        "tax": tax, "discount": discount, "tip": tip, "total": total
    }


@app.get("/")
def root():
    return {"app": "ShiftBite", "version": "2.0.0",
            "message": "Good Food • Great Mood",
            "portals": ["Admin", "Restaurant", "Delivery", "Customer"],
            "docs": "/docs"}


@app.get(V1 + "/health")
def health():
    return {"status": "healthy", "application": "ShiftBite"}


# AUTHENTICATION: public registration creates customer accounts only.
@app.post(V1 + "/auth/register")
def register(data: s.RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(m.User).filter(or_(
        m.User.email == data.email,
        m.User.phone == data.phone if data.phone else False
    )).first()
    if existing:
        raise HTTPException(409, "Email or phone already registered")
    user = m.User(name=data.name, email=data.email, phone=data.phone,
                  password_hash=hash_password(data.password),
                  role="customer", status="active")
    db.add(user)
    commit_changes(db)
    db.refresh(user)
    return {"message": "Customer account created",
            "user_id": user.user_id, "role": user.role}


@app.post(V1 + "/auth/register/restaurant")
def register_restaurant(data: dict, db: Session = Depends(get_db)):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    phone = data.get("phone")
    restaurant_name = str(data.get("restaurant_name", "")).strip()
    address = str(data.get("address", "")).strip()
    if not all([name, email, password, restaurant_name, address]):
        raise HTTPException(400, "Name, email, password, restaurant name and address are required")
    if len(password) < 8:
        raise HTTPException(400, "Password must contain at least 8 characters")
    existing = db.query(m.User).filter(or_(
        m.User.email == email,
        m.User.phone == phone if phone else False
    )).first()
    if existing:
        raise HTTPException(409, "Email or phone already registered")
    try:
        owner = m.User(name=name, email=email, phone=phone,
                       password_hash=hash_password(password),
                       role="restaurant_owner", status="active")
        db.add(owner)
        db.flush()
        restaurant = m.Restaurant(
            owner_id=owner.user_id, name=restaurant_name, address=address,
            cuisine=data.get("cuisine"), image_url=data.get("image_url"),
            status="pending", is_open=False
        )
        db.add(restaurant)
        db.commit()
        db.refresh(owner)
        db.refresh(restaurant)
        return {"message": "Restaurant registration submitted for admin approval",
                "user_id": owner.user_id, "restaurant_id": restaurant.restaurant_id,
                "role": owner.role, "status": restaurant.status}
    except Exception:
        db.rollback()
        raise


@app.post(V1 + "/auth/register/delivery")
def register_delivery(data: dict, db: Session = Depends(get_db)):
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    phone = data.get("phone")
    if not name or not email or not password:
        raise HTTPException(400, "Name, email and password are required")
    if len(password) < 8:
        raise HTTPException(400, "Password must contain at least 8 characters")
    existing = db.query(m.User).filter(or_(
        m.User.email == email,
        m.User.phone == phone if phone else False
    )).first()
    if existing:
        raise HTTPException(409, "Email or phone already registered")
    try:
        partner_user = m.User(name=name, email=email, phone=phone,
                              password_hash=hash_password(password),
                              role="delivery_partner", status="active")
        db.add(partner_user)
        db.flush()
        db.add(m.DeliveryPartner(user_id=partner_user.user_id,
                                 availability="offline", vehicle=data.get("vehicle")))
        db.commit()
        db.refresh(partner_user)
        return {"message": "Delivery partner account created",
                "user_id": partner_user.user_id, "role": partner_user.role}
    except Exception:
        db.rollback()
        raise


@app.post(V1 + "/auth/login")
def login(data: s.LoginIn, db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if user.status != "active":
        raise HTTPException(403, "Account is not active")
    return {"access_token": create_token(user), "token_type": "bearer",
            "role": user.role, "name": user.name, "user_id": user.user_id}
@app.post(V1 + "/auth/token")
def swagger_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(m.User).filter(
        m.User.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=403,
            detail="Account is not active"
        )

    return {
        "access_token": create_token(user),
        "token_type": "bearer"
    }

@app.post(V1 + "/auth/logout")
def logout(user=Depends(current_user)):
    return {"message": "Logged out. Remove the bearer token from the client."}


@app.get(V1 + "/auth/me")
def me(user=Depends(current_user)):
    return {"user_id": user.user_id, "name": user.name,
            "email": user.email, "phone": user.phone, "role": user.role}


@app.get(V1 + "/users/me")
def profile(user=Depends(current_user)):
    return me(user)


@app.put(V1 + "/users/me")
def update_profile(data: dict, user=Depends(current_user), db: Session = Depends(get_db)):
    if "name" in data:
        user.name = str(data["name"]).strip()
    if "phone" in data:
        phone = data["phone"]
        if phone and db.query(m.User).filter(
            m.User.phone == phone, m.User.user_id != user.user_id
        ).first():
            raise HTTPException(409, "Phone number already registered")
        user.phone = phone
    commit_changes(db)
    return {"message": "Profile updated"}


# CUSTOMER ADDRESSES
@app.get(V1 + "/users/me/addresses")
def addresses(user=Depends(allow("customer")), db: Session = Depends(get_db)):
    return db.query(m.Address).filter_by(user_id=user.user_id).all()


@app.post(V1 + "/users/me/addresses")
def add_address(data: s.AddressIn, user=Depends(allow("customer")),
                db: Session = Depends(get_db)):
    if data.is_default:
        db.query(m.Address).filter_by(user_id=user.user_id).update({"is_default": False})
    row = m.Address(user_id=user.user_id, **data.model_dump())
    db.add(row)
    commit_changes(db)
    db.refresh(row)
    return row


@app.put(V1 + "/users/me/addresses/{address_id}")
def edit_address(address_id: int, data: s.AddressIn,
                 user=Depends(allow("customer")), db: Session = Depends(get_db)):
    row = db.query(m.Address).filter_by(
        address_id=address_id, user_id=user.user_id
    ).first()
    if not row:
        raise HTTPException(404, "Address not found")
    if data.is_default:
        db.query(m.Address).filter_by(user_id=user.user_id).update({"is_default": False})
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    commit_changes(db)
    return row


@app.delete(V1 + "/users/me/addresses/{address_id}")
def delete_address(address_id: int, user=Depends(allow("customer")),
                   db: Session = Depends(get_db)):
    row = db.query(m.Address).filter_by(
        address_id=address_id, user_id=user.user_id
    ).first()
    if not row:
        raise HTTPException(404, "Address not found")
    db.delete(row)
    commit_changes(db)
    return {"message": "Address deleted"}


# CUSTOMER DISCOVERY
@app.get(V1 + "/home")
def home(db: Session = Depends(get_db)):
    return {
        "restaurants": db.query(m.Restaurant).filter_by(
            status="approved", is_open=True).limit(10).all(),
        "popular_items": db.query(m.MenuItem).join(m.Restaurant).filter(
            m.MenuItem.is_available == True, m.Restaurant.status == "approved",
            m.Restaurant.is_open == True).limit(10).all()
    }


@app.get(V1 + "/restaurants")
def restaurants(q: str | None = None, cuisine: str | None = None,
                veg: bool | None = None, db: Session = Depends(get_db)):
    query = db.query(m.Restaurant).filter(
        m.Restaurant.status == "approved", m.Restaurant.is_open == True)
    if q:
        query = query.filter(m.Restaurant.name.ilike(f"%{q}%"))
    if cuisine:
        query = query.filter(m.Restaurant.cuisine.ilike(f"%{cuisine}%"))
    if veg is not None:
        query = query.join(m.MenuItem).filter(
            m.MenuItem.is_available == True, m.MenuItem.is_veg == veg).distinct()
    return query.all()


@app.get(V1 + "/search")
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    rests = db.query(m.Restaurant).filter(
        m.Restaurant.status == "approved", m.Restaurant.is_open == True,
        m.Restaurant.name.ilike(f"%{q}%")).all()
    items = db.query(m.MenuItem).join(m.Restaurant).filter(
        m.MenuItem.is_available == True, m.Restaurant.status == "approved",
        m.Restaurant.is_open == True, m.MenuItem.name.ilike(f"%{q}%")).all()
    return {"restaurants": rests, "items": items}


@app.get(V1 + "/restaurants/{restaurant_id}")
def restaurant_detail(restaurant_id: int, db: Session = Depends(get_db)):
    row = db.query(m.Restaurant).filter_by(
        restaurant_id=restaurant_id, status="approved", is_open=True).first()
    if not row:
        raise HTTPException(404, "Restaurant not found")
    return row


@app.get(V1 + "/restaurants/{restaurant_id}/menu")
def menu(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(m.Restaurant).filter_by(
        restaurant_id=restaurant_id, status="approved", is_open=True).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    return db.query(m.MenuItem).filter_by(
        restaurant_id=restaurant_id, is_available=True).all()


@app.get(V1 + "/menu-items/{item_id}")
def item_detail(item_id: int, db: Session = Depends(get_db)):
    row = db.query(m.MenuItem).filter_by(item_id=item_id, is_available=True).first()
    if not row:
        raise HTTPException(404, "Menu item not found")
    return row


# RESTAURANT PORTAL
@app.get(V1 + "/restaurant-portal/profile")
def restaurant_profile(user=Depends(allow("restaurant_owner")),
                       db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant profile not found")
    return restaurant


@app.patch(V1 + "/restaurant-portal/profile")
def update_restaurant_profile(data: dict, user=Depends(allow("restaurant_owner")),
                              db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant profile not found")
    if restaurant.status != "approved":
        raise HTTPException(403, "Restaurant is awaiting admin approval")
    for key in ("name", "address", "cuisine", "image_url"):
        if key in data:
            setattr(restaurant, key, data[key])
    commit_changes(db)
    return {"message": "Restaurant profile updated"}


@app.patch(V1 + "/restaurant-portal/availability")
def restaurant_availability(data: s.AvailabilityIn,
                            user=Depends(allow("restaurant_owner")),
                            db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    if restaurant.status != "approved":
        raise HTTPException(403, "Restaurant is not approved")
    if data.availability not in ("online", "offline"):
        raise HTTPException(400, "Use online or offline")
    restaurant.is_open = data.availability == "online"
    commit_changes(db)
    return {"is_open": restaurant.is_open}


@app.post(V1 + "/restaurant-portal/menu")
def create_menu(data: s.MenuItemIn, user=Depends(allow("restaurant_owner")),
                db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Create a restaurant profile first")
    if restaurant.status != "approved":
        raise HTTPException(403, "Restaurant is awaiting approval")
    row = m.MenuItem(restaurant_id=restaurant.restaurant_id, **data.model_dump())
    db.add(row)
    commit_changes(db)
    db.refresh(row)
    return row


@app.get(V1 + "/restaurant-portal/menu")
def own_menu(user=Depends(allow("restaurant_owner")), db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        return []
    return db.query(m.MenuItem).filter_by(restaurant_id=restaurant.restaurant_id).all()


@app.put(V1 + "/restaurant-portal/menu/{item_id}")
def update_menu(item_id: int, data: s.MenuItemIn,
                user=Depends(allow("restaurant_owner")), db: Session = Depends(get_db)):
    row = db.query(m.MenuItem).join(m.Restaurant).filter(
        m.MenuItem.item_id == item_id, m.Restaurant.owner_id == user.user_id).first()
    if not row:
        raise HTTPException(404, "Menu item not found")
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    commit_changes(db)
    return row


@app.delete(V1 + "/restaurant-portal/menu/{item_id}")
def remove_menu(item_id: int, user=Depends(allow("restaurant_owner")),
                db: Session = Depends(get_db)):
    row = db.query(m.MenuItem).join(m.Restaurant).filter(
        m.MenuItem.item_id == item_id, m.Restaurant.owner_id == user.user_id).first()
    if not row:
        raise HTTPException(404, "Menu item not found")
    row.is_available = False
    commit_changes(db)
    return {"message": "Menu item archived"}


# RESTAURANT ORDERS
@app.get(V1 + "/restaurant-portal/orders")
def restaurant_orders(status: str | None = None,
                      user=Depends(allow("restaurant_owner")),
                      db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    query = db.query(m.Order).filter(m.Order.restaurant_id == restaurant.restaurant_id)
    if status:
        query = query.filter(m.Order.status == status)
    return query.order_by(m.Order.created_at.desc()).all()


@app.get(V1 + "/restaurant-portal/orders/{order_id}")
def restaurant_order_detail(order_id: int,
                            user=Depends(allow("restaurant_owner")),
                            db: Session = Depends(get_db)):
    order = restaurant_order(db, order_id, user.user_id)
    return {"order": order,
            "items": db.query(m.OrderItem).filter_by(order_id=order_id).all()}


@app.patch(V1 + "/restaurant-portal/orders/{order_id}/decision")
def restaurant_order_decision(order_id: int, data: s.DecisionIn,
                              user=Depends(allow("restaurant_owner")),
                              db: Session = Depends(get_db)):
    order = restaurant_order(db, order_id, user.user_id)
    if order.status != "placed":
        raise HTTPException(400, "Order has already been processed")
    decision = data.decision.lower()
    if decision == "accept":
        if data.preparation_minutes is not None and not 1 <= data.preparation_minutes <= 240:
            raise HTTPException(400, "Invalid preparation time")
        order.status = "accepted"
        notify(db, order.user_id, f"Restaurant accepted your order #{order_id}.")
    elif decision == "reject":
        order.status = "rejected"
        notify(db, order.user_id, f"Restaurant rejected your order #{order_id}.")
    else:
        raise HTTPException(400, "Decision must be accept or reject")
    commit_changes(db)
    return {"order_id": order_id, "status": order.status}


@app.patch(V1 + "/restaurant-portal/orders/{order_id}/status")
def restaurant_order_status(order_id: int, data: s.StatusIn,
                             user=Depends(allow("restaurant_owner")),
                             db: Session = Depends(get_db)):
    order = restaurant_order(db, order_id, user.user_id)
    transitions = {"accepted": "preparing", "preparing": "ready_for_pickup"}
    if transitions.get(order.status) != data.status:
        raise HTTPException(400, "Invalid restaurant order status transition")
    order.status = data.status
    notify(db, order.user_id, f"Your order #{order_id} is now {data.status}.")
    commit_changes(db)
    return {"order_id": order_id, "status": order.status}


@app.get(V1 + "/restaurant-portal/dashboard/stats")
def restaurant_dashboard_stats(user=Depends(allow("restaurant_owner")),
                               db: Session = Depends(get_db)):
    restaurant = get_restaurant(db, user.user_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    orders = db.query(m.Order).filter_by(restaurant_id=restaurant.restaurant_id)
    revenue = db.query(func.coalesce(func.sum(m.Order.total_amount), 0)).filter(
        m.Order.restaurant_id == restaurant.restaurant_id,
        m.Order.status == "delivered").scalar()
    return {
        "restaurant": restaurant.name, "total_orders": orders.count(),
        "new_orders": orders.filter_by(status="placed").count(),
        "accepted_orders": orders.filter_by(status="accepted").count(),
        "preparing_orders": orders.filter_by(status="preparing").count(),
        "ready_orders": orders.filter_by(status="ready_for_pickup").count(),
        "completed_orders": orders.filter_by(status="delivered").count(),
        "revenue": float(revenue)
    }


# CUSTOMER CART
@app.get(V1 + "/cart")
def get_cart(user=Depends(allow("customer")), db: Session = Depends(get_db)):
    rows = db.query(m.CartItem, m.MenuItem).join(
        m.MenuItem, m.CartItem.item_id == m.MenuItem.item_id
    ).filter(m.CartItem.user_id == user.user_id).all()
    items = [{
        "cart_item_id": c.cart_item_id, "item_id": i.item_id,
        "restaurant_id": i.restaurant_id, "name": i.name,
        "quantity": c.quantity, "unit_price": float(i.price),
        "customization": c.customization,
        "subtotal": float(i.price) * c.quantity
    } for c, i in rows]
    return {"items": items, "subtotal": sum(x["subtotal"] for x in items)}


@app.post(V1 + "/cart/items")
def add_cart(data: s.CartIn, user=Depends(allow("customer")),
             db: Session = Depends(get_db)):
    item = db.query(m.MenuItem).join(m.Restaurant).filter(
        m.MenuItem.item_id == data.item_id,
        m.MenuItem.is_available == True,
        m.Restaurant.status == "approved",
        m.Restaurant.is_open == True
    ).first()
    if not item:
        raise HTTPException(404, "Available menu item not found")

    existing = db.query(m.CartItem, m.MenuItem).join(m.MenuItem).filter(
        m.CartItem.user_id == user.user_id).all()
    if any(other.restaurant_id != item.restaurant_id for c, other in existing):
        raise HTTPException(400, "Your cart contains items from another restaurant. Clear it first")

    row = db.query(m.CartItem).filter_by(
        user_id=user.user_id, item_id=data.item_id,
        customization=data.customization).first()
    if row:
        if row.quantity + data.quantity > 50:
            raise HTTPException(400, "Maximum quantity is 50")
        row.quantity += data.quantity
    else:
        db.add(m.CartItem(user_id=user.user_id, **data.model_dump()))
    commit_changes(db)
    return get_cart(user, db)


@app.patch(V1 + "/cart/items/{cart_item_id}")
def update_cart(cart_item_id: int, data: s.CartIn,
                user=Depends(allow("customer")), db: Session = Depends(get_db)):
    row = db.query(m.CartItem).filter_by(
        cart_item_id=cart_item_id, user_id=user.user_id).first()
    if not row:
        raise HTTPException(404, "Cart item not found")
    if row.item_id != data.item_id:
        raise HTTPException(400, "Cart item cannot be changed to another item")
    row.quantity = data.quantity
    row.customization = data.customization
    commit_changes(db)
    return get_cart(user, db)


@app.delete(V1 + "/cart/items/{cart_item_id}")
def remove_cart(cart_item_id: int, user=Depends(allow("customer")),
                db: Session = Depends(get_db)):
    row = db.query(m.CartItem).filter_by(
        cart_item_id=cart_item_id, user_id=user.user_id).first()
    if not row:
        raise HTTPException(404, "Cart item not found")
    db.delete(row)
    commit_changes(db)
    return get_cart(user, db)


# CHECKOUT AND ORDERS
@app.post(V1 + "/checkout/validate")
def validate_checkout(data: s.CheckoutIn, user=Depends(allow("customer")),
                      db: Session = Depends(get_db)):
    x = checkout_summary(data, user, db)
    return {
        "subtotal": float(x["subtotal"]), "delivery_fee": float(x["delivery"]),
        "packaging_fee": float(x["packaging"]), "tax": float(x["tax"]),
        "discount": float(x["discount"]), "tip": float(x["tip"]),
        "total": float(x["total"]), "address": x["address"].address_text
    }


@app.post(V1 + "/orders")
def place_order(data: s.CheckoutIn, user=Depends(allow("customer")),
                db: Session = Depends(get_db)):
    x = checkout_summary(data, user, db)
    try:
        order = m.Order(user_id=user.user_id, restaurant_id=x["restaurant_id"],
                        total_amount=x["total"],
                        delivery_address=x["address"].address_text, status="placed")
        db.add(order)
        db.flush()
        for cart_item, item in x["cart"]:
            db.add(m.OrderItem(
                order_id=order.order_id, item_id=item.item_id,
                quantity=cart_item.quantity, unit_price=item.price,
                customization=cart_item.customization))
        db.add(m.Payment(order_id=order.order_id, method=data.payment_method,
                         amount=x["total"], status="pending"))
        db.query(m.CartItem).filter_by(user_id=user.user_id).delete()
        restaurant = db.query(m.Restaurant).filter_by(
            restaurant_id=x["restaurant_id"]).first()
        notify(db, user.user_id, f"Your ShiftBite order #{order.order_id} has been placed.")
        if restaurant:
            notify(db, restaurant.owner_id, f"New order received: #{order.order_id}.")
        db.commit()
        db.refresh(order)
        return {"order_id": order.order_id, "status": order.status,
                "total": float(order.total_amount)}
    except Exception:
        db.rollback()
        raise


@app.get(V1 + "/orders")
def my_orders(user=Depends(allow("customer")), db: Session = Depends(get_db)):
    return db.query(m.Order).filter_by(user_id=user.user_id).order_by(
        m.Order.created_at.desc()).all()


@app.get(V1 + "/orders/{order_id}")
def order_detail(order_id: int, user=Depends(current_user),
                 db: Session = Depends(get_db)):
    order = db.query(m.Order).filter_by(order_id=order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    allowed = user.role == "admin"
    if user.role == "customer":
        allowed = order.user_id == user.user_id
    elif user.role == "restaurant_owner":
        restaurant = get_restaurant(db, user.user_id)
        allowed = bool(restaurant and restaurant.restaurant_id == order.restaurant_id)
    elif user.role == "delivery_partner":
        partner = get_partner(db, user.user_id)
        allowed = bool(partner and db.query(m.Delivery).filter_by(
            order_id=order_id, partner_id=partner.partner_id).first())
    if not allowed:
        raise HTTPException(403, "You cannot access this order")
    return {
        "order": order,
        "items": db.query(m.OrderItem).filter_by(order_id=order_id).all(),
        "payments": db.query(m.Payment).filter_by(order_id=order_id).all()
    }


@app.post(V1 + "/orders/{order_id}/cancel")
def cancel_order(order_id: int, user=Depends(allow("customer")),
                 db: Session = Depends(get_db)):
    order = db.query(m.Order).filter_by(
        order_id=order_id, user_id=user.user_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != "placed":
        raise HTTPException(400, "Only newly placed orders can be cancelled")
    order.status = "cancelled"
    notify(db, user.user_id, f"Order #{order_id} was cancelled.")
    commit_changes(db)
    return {"status": order.status}


# PAYMENTS: webhook intentionally remains disabled until a provider is configured.
@app.get(V1 + "/payments/{payment_id}")
def payment_status(payment_id: int, user=Depends(current_user),
                   db: Session = Depends(get_db)):
    payment = db.query(m.Payment).filter_by(payment_id=payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    order = db.query(m.Order).filter_by(order_id=payment.order_id).first()
    if user.role != "admin" and order.user_id != user.user_id:
        raise HTTPException(403, "Forbidden")
    return payment


@app.post(V1 + "/payments/webhook")
def payment_webhook(payload: dict):
    return {"received": False,
            "message": "Payment provider integration is not configured."}


# DELIVERY PARTNER PORTAL
@app.post(V1 + "/delivery-partners/me/register")
def register_delivery_partner(vehicle: str = "",
                              user=Depends(allow("delivery_partner")),
                              db: Session = Depends(get_db)):
    existing = get_partner(db, user.user_id)
    if existing:
        return existing
    row = m.DeliveryPartner(user_id=user.user_id, vehicle=vehicle,
                            availability="offline")
    db.add(row)
    commit_changes(db)
    db.refresh(row)
    return row


@app.get(V1 + "/delivery-partners/me")
def delivery_profile(user=Depends(allow("delivery_partner")),
                     db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    return partner


@app.patch(V1 + "/delivery-partners/me/availability")
def set_availability(data: s.AvailabilityIn,
                     user=Depends(allow("delivery_partner")),
                     db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    if data.availability not in ("online", "offline"):
        raise HTTPException(400, "Use online or offline")
    if data.availability == "offline":
        active = db.query(m.Delivery).filter(
            m.Delivery.partner_id == partner.partner_id,
            m.Delivery.status.in_(["assigned", "accepted", "arrived_restaurant",
                                   "picked_up", "on_the_way"])).first()
        if active:
            raise HTTPException(400, "Complete your active delivery before going offline")
    partner.availability = data.availability
    commit_changes(db)
    return partner


@app.get(V1 + "/delivery-partners/me/requests")
def delivery_requests(user=Depends(allow("delivery_partner")),
                      db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    return db.query(m.Delivery).filter_by(
        partner_id=partner.partner_id).order_by(m.Delivery.assigned_at.desc()).all()


@app.get(V1 + "/delivery-partners/me/dashboard")
def delivery_dashboard(user=Depends(allow("delivery_partner")),
                       db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    deliveries = db.query(m.Delivery).filter_by(partner_id=partner.partner_id)
    return {
        "availability": partner.availability,
        "total_deliveries": deliveries.count(),
        "active_deliveries": deliveries.filter(m.Delivery.status.in_(
            ["assigned", "accepted", "arrived_restaurant", "picked_up", "on_the_way"]
        )).count(),
        "completed_deliveries": deliveries.filter_by(status="delivered").count()
    }


# ADMIN DELIVERY ASSIGNMENT
@app.post(V1 + "/admin/orders/{order_id}/assign")
def assign_delivery(order_id: int, data: s.DeliveryAssignIn,
                    user=Depends(allow("admin")), db: Session = Depends(get_db)):
    order = db.query(m.Order).filter_by(order_id=order_id).first()
    partner = db.query(m.DeliveryPartner).filter_by(
        partner_id=data.partner_id, availability="online").first()
    if not order:
        raise HTTPException(404, "Order not found")
    if not partner:
        raise HTTPException(404, "Online delivery partner not found")
    if order.status != "ready_for_pickup":
        raise HTTPException(400, "Restaurant must mark the order ready before assignment")
    existing = db.query(m.Delivery).filter(
        m.Delivery.order_id == order_id, m.Delivery.status != "cancelled").first()
    if existing:
        raise HTTPException(409, "This order already has a delivery assignment")
    active = db.query(m.Delivery).filter(
        m.Delivery.partner_id == partner.partner_id,
        m.Delivery.status.in_(["assigned", "accepted", "arrived_restaurant",
                               "picked_up", "on_the_way"])).first()
    if active:
        raise HTTPException(409, "Delivery partner already has an active delivery")
    delivery = m.Delivery(order_id=order_id, partner_id=partner.partner_id,
                          status="assigned")
    db.add(delivery)
    notify(db, partner.user_id, f"New ShiftBite delivery assignment for order #{order_id}.")
    commit_changes(db)
    db.refresh(delivery)
    return delivery


@app.post(V1 + "/deliveries/{delivery_id}/accept")
def accept_delivery(delivery_id: int, user=Depends(allow("delivery_partner")),
                    db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    row = db.query(m.Delivery).filter_by(
        delivery_id=delivery_id, partner_id=partner.partner_id).first()
    if not row:
        raise HTTPException(404, "Delivery assignment not found")
    if row.status != "assigned":
        raise HTTPException(400, "Assignment cannot be accepted")
    row.status = "accepted"
    commit_changes(db)
    return {"message": "Delivery accepted", "delivery_id": row.delivery_id,
            "status": row.status}


@app.patch(V1 + "/deliveries/{delivery_id}/status")
def delivery_status(delivery_id: int, data: s.StatusIn,
                    user=Depends(allow("delivery_partner")),
                    db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    row = db.query(m.Delivery).filter_by(
        delivery_id=delivery_id, partner_id=partner.partner_id).first()
    if not row:
        raise HTTPException(404, "Delivery not found")
    transitions = {
        "accepted": "arrived_restaurant",
        "arrived_restaurant": "picked_up",
        "picked_up": "on_the_way",
        "on_the_way": "delivered"
    }
    if transitions.get(row.status) != data.status:
        raise HTTPException(400, "Invalid delivery status transition")
    order = db.query(m.Order).filter_by(order_id=row.order_id).first()
    if not order:
        raise HTTPException(404, "Related order not found")
    row.status = data.status
    order.status = {
        "arrived_restaurant": "ready_for_pickup",
        "picked_up": "picked_up",
        "on_the_way": "on_the_way",
        "delivered": "delivered"
    }[data.status]
    if data.status == "delivered":
        row.delivered_at = datetime.now(timezone.utc)
        partner.availability = "online"
    notify(db, order.user_id, f"Your order #{order.order_id} is now {data.status}.")
    restaurant = db.query(m.Restaurant).filter_by(
        restaurant_id=order.restaurant_id).first()
    if restaurant:
        notify(db, restaurant.owner_id,
               f"Order #{order.order_id} delivery update: {data.status}.")
    commit_changes(db)
    return {"delivery_status": row.status, "order_status": order.status}


@app.patch(V1 + "/deliveries/{delivery_id}/location")
def update_location(delivery_id: int, data: s.LocationIn,
                    user=Depends(allow("delivery_partner")),
                    db: Session = Depends(get_db)):
    partner = get_partner(db, user.user_id)
    if not partner:
        raise HTTPException(404, "Delivery profile not found")
    row = db.query(m.Delivery).filter_by(
        delivery_id=delivery_id, partner_id=partner.partner_id).first()
    if not row:
        raise HTTPException(404, "Delivery not found")
    row.current_location = data.location
    partner.current_location = data.location
    commit_changes(db)
    return {"message": "Latest location saved"}


# TRACKING
@app.get(V1 + "/orders/{order_id}/tracking")
def tracking(order_id: int, user=Depends(current_user),
             db: Session = Depends(get_db)):
    order = db.query(m.Order).filter_by(order_id=order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    allowed = user.role == "admin"
    if user.role == "customer":
        allowed = order.user_id == user.user_id
    elif user.role == "restaurant_owner":
        restaurant = get_restaurant(db, user.user_id)
        allowed = bool(restaurant and restaurant.restaurant_id == order.restaurant_id)
    elif user.role == "delivery_partner":
        partner = get_partner(db, user.user_id)
        allowed = bool(partner and db.query(m.Delivery).filter_by(
            order_id=order_id, partner_id=partner.partner_id).first())
    if not allowed:
        raise HTTPException(403, "Forbidden")
    delivery = db.query(m.Delivery).filter_by(order_id=order_id).order_by(
        m.Delivery.delivery_id.desc()).first()
    return {"order_id": order.order_id, "order_status": order.status,
            "delivery": delivery,
            "note": "GPS/map ETA requires configured provider integration."}


# ADMIN DASHBOARD
@app.get(V1 + "/admin/dashboard/stats")
def admin_dashboard_stats(user=Depends(allow("admin")),
                          db: Session = Depends(get_db)):
    revenue = db.query(func.coalesce(func.sum(m.Order.total_amount), 0)).filter_by(
        status="delivered").scalar()
    return {
        "total_users": db.query(m.User).count(),
        "total_customers": db.query(m.User).filter_by(role="customer").count(),
        "total_restaurants": db.query(m.Restaurant).count(),
        "pending_restaurants": db.query(m.Restaurant).filter_by(status="pending").count(),
        "approved_restaurants": db.query(m.Restaurant).filter_by(status="approved").count(),
        "total_delivery_partners": db.query(m.DeliveryPartner).count(),
        "total_orders": db.query(m.Order).count(),
        "pending_orders": db.query(m.Order).filter_by(status="placed").count(),
        "completed_orders": db.query(m.Order).filter_by(status="delivered").count(),
        "total_revenue": float(revenue)
    }


@app.get(V1 + "/admin/users")
def admin_users(role: str | None = None, user=Depends(allow("admin")),
                db: Session = Depends(get_db)):
    query = db.query(m.User)
    if role:
        if role not in ROLES:
            raise HTTPException(400, "Invalid role")
        query = query.filter(m.User.role == role)
    return query.order_by(m.User.created_at.desc()).all()


@app.patch(V1 + "/admin/users/{user_id}/status")
def admin_update_user_status(user_id: int, data: s.StatusIn,
                              user=Depends(allow("admin")), db: Session = Depends(get_db)):
    target = db.query(m.User).filter_by(user_id=user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if target.role == "admin":
        raise HTTPException(403, "Admin account cannot be modified here")
    if data.status not in ("active", "inactive", "suspended"):
        raise HTTPException(400, "Invalid account status")
    target.status = data.status
    commit_changes(db)
    return {"user_id": target.user_id, "status": target.status}


# ADMIN RESTAURANTS
@app.get(V1 + "/admin/restaurants")
def admin_restaurants(status: str | None = None,
                      user=Depends(allow("admin")), db: Session = Depends(get_db)):
    query = db.query(m.Restaurant)
    if status:
        query = query.filter(m.Restaurant.status == status)
    return query.order_by(m.Restaurant.restaurant_id.desc()).all()


@app.post(V1 + "/admin/restaurants/{restaurant_id}/approve")
def approve_restaurant(restaurant_id: int, user=Depends(allow("admin")),
                       db: Session = Depends(get_db)):
    restaurant = db.query(m.Restaurant).filter_by(
        restaurant_id=restaurant_id).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    restaurant.status = "approved"
    restaurant.is_open = True
    notify(db, restaurant.owner_id,
           f"Congratulations! {restaurant.name} has been approved on ShiftBite.")
    commit_changes(db)
    return {"message": "Restaurant approved",
            "restaurant_id": restaurant.restaurant_id, "status": restaurant.status}


@app.post(V1 + "/admin/restaurants/{restaurant_id}/reject")
def reject_restaurant(restaurant_id: int, user=Depends(allow("admin")),
                      db: Session = Depends(get_db)):
    restaurant = db.query(m.Restaurant).filter_by(
        restaurant_id=restaurant_id).first()
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    restaurant.status = "rejected"
    restaurant.is_open = False
    notify(db, restaurant.owner_id, f"Your restaurant {restaurant.name} was not approved.")
    commit_changes(db)
    return {"message": "Restaurant rejected",
            "restaurant_id": restaurant.restaurant_id, "status": restaurant.status}


@app.get(V1 + "/admin/orders")
def admin_orders(status: str | None = None,
                 user=Depends(allow("admin")), db: Session = Depends(get_db)):
    query = db.query(m.Order)
    if status:
        query = query.filter(m.Order.status == status)
    return query.order_by(m.Order.created_at.desc()).all()


@app.get(V1 + "/admin/delivery-partners")
def admin_delivery_partners(user=Depends(allow("admin")),
                            db: Session = Depends(get_db)):
    return db.query(m.DeliveryPartner).all()


# NOTIFICATIONS
@app.get(V1 + "/notifications")
def notifications(user=Depends(current_user), db: Session = Depends(get_db)):
    return db.query(m.Notification).filter_by(user_id=user.user_id).order_by(
        m.Notification.created_at.desc()).all()


@app.patch(V1 + "/notifications/{notification_id}/read")
def read_notification(notification_id: int, user=Depends(current_user),
                      db: Session = Depends(get_db)):
    row = db.query(m.Notification).filter_by(
        notification_id=notification_id, user_id=user.user_id).first()
    if not row:
        raise HTTPException(404, "Notification not found")
    row.status = "read"
    commit_changes(db)
    return {"message": "Marked as read"}


# REVIEWS
@app.post(V1 + "/orders/{order_id}/reviews")
def create_review(order_id: int, data: s.ReviewIn,
                  user=Depends(allow("customer")), db: Session = Depends(get_db)):
    order = db.query(m.Order).filter_by(
        order_id=order_id, user_id=user.user_id, status="delivered").first()
    if not order:
        raise HTTPException(400, "Only completed orders can be reviewed")
    if db.query(m.Review).filter_by(order_id=order_id, user_id=user.user_id).first():
        raise HTTPException(409, "You have already reviewed this order")
    review = m.Review(
        order_id=order_id, user_id=user.user_id,
        restaurant_id=order.restaurant_id,
        food_rating=data.food_rating,
        delivery_rating=data.delivery_rating,
        comment=data.comment
    )
    db.add(review)
    commit_changes(db)
    average = db.query(func.avg(m.Review.food_rating)).filter_by(
        restaurant_id=order.restaurant_id).scalar()
    restaurant = db.query(m.Restaurant).filter_by(
        restaurant_id=order.restaurant_id).first()
    if restaurant and average is not None:
        restaurant.rating = Decimal(str(average)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP)
        commit_changes(db)
    return {"message": "Review submitted successfully", "review_id": review.review_id}


@app.get(V1 + "/restaurants/{restaurant_id}/reviews")
def restaurant_reviews(restaurant_id: int, db: Session = Depends(get_db)):
    return db.query(m.Review).filter_by(restaurant_id=restaurant_id).all()


# SUPPORT
@app.post(V1 + "/support/tickets")
def create_ticket(data: s.TicketIn, user=Depends(current_user),
                  db: Session = Depends(get_db)):
    if data.order_id is not None:
        order = db.query(m.Order).filter_by(
            order_id=data.order_id, user_id=user.user_id).first()
        if not order and user.role != "admin":
            raise HTTPException(404, "Order not found")
    ticket = m.SupportTicket(
        user_id=user.user_id, order_id=data.order_id,
        subject=data.subject, status="open")
    db.add(ticket)
    commit_changes(db)
    db.refresh(ticket)
    return {"message": "Support ticket created", "ticket_id": ticket.ticket_id}


@app.get(V1 + "/support/tickets")
def my_tickets(user=Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(m.SupportTicket)
    if user.role != "admin":
        query = query.filter(m.SupportTicket.user_id == user.user_id)
    return query.order_by(m.SupportTicket.ticket_id.desc()).all()


@app.patch(V1 + "/admin/support/tickets/{ticket_id}")
def update_ticket(ticket_id: int, data: dict, user=Depends(allow("admin")),
                  db: Session = Depends(get_db)):
    ticket = db.query(m.SupportTicket).filter_by(ticket_id=ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if "status" in data:
        if data["status"] not in ("open", "in_progress", "resolved", "closed"):
            raise HTTPException(400, "Invalid ticket status")
        ticket.status = data["status"]
    if "resolution" in data:
        ticket.resolution = data["resolution"]
    notify(db, ticket.user_id, f"Your support ticket #{ticket_id} has been updated.")
    commit_changes(db)
    return {"message": "Support ticket updated", "status": ticket.status}
