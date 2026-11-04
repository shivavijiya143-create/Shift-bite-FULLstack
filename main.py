from datetime import datetime, timezone
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from .database import Base, engine, get_db
from . import models as m, schemas as s
from .security import hash_password, verify_password, create_token, current_user, allow

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ShiftBite API", version="1.0.0",
              description="Food delivery application API for the ShiftBite BCA project.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
V1 = "/api/v1"

def notify(db, user_id, message):
    db.add(m.Notification(user_id=user_id, message=message, channel="in_app", status="queued"))

@app.get("/")
def root(): return {"app":"ShiftBite","message":"Good Food • Great Mood","docs":"/docs"}

# 1. Authentication and user management
@app.post(V1+"/auth/register")
def register(data:s.RegisterIn, db:Session=Depends(get_db)):
    if db.query(m.User).filter(or_(m.User.email==data.email, m.User.phone==data.phone if data.phone else False)).first():
        raise HTTPException(409,"Email or phone already registered")
    user=m.User(name=data.name,email=data.email,phone=data.phone,password_hash=hash_password(data.password),role="customer")
    db.add(user); db.commit(); db.refresh(user)
    return {"message":"Account created","user_id":user.user_id,"role":user.role}

@app.post(V1+"/auth/login")
def login(data:s.LoginIn, db:Session=Depends(get_db)):
    user=db.query(m.User).filter(m.User.email==data.email).first()
    if not user or not verify_password(data.password,user.password_hash):
        raise HTTPException(401,"Invalid email or password")
    if user.status!="active": raise HTTPException(403,"Account is not active")
    return {"access_token":create_token(user),"token_type":"bearer","role":user.role,"name":user.name}

@app.post(V1+"/auth/logout")
def logout(user=Depends(current_user)):
    return {"message":"Logged out. Remove the bearer token from the client."}

@app.get(V1+"/auth/me")
def me(user=Depends(current_user)):
    return {"user_id":user.user_id,"name":user.name,"email":user.email,"phone":user.phone,"role":user.role}

@app.get(V1+"/users/me")
def profile(user=Depends(current_user)): return me(user)

@app.put(V1+"/users/me")
def update_profile(data:dict,user=Depends(current_user),db:Session=Depends(get_db)):
    for key in ("name","phone"):
        if key in data: setattr(user,key,data[key])
    db.commit(); return {"message":"Profile updated"}

# 2. Location and address management
@app.get(V1+"/users/me/addresses")
def addresses(user=Depends(allow("customer")),db:Session=Depends(get_db)):
    return db.query(m.Address).filter_by(user_id=user.user_id).all()

@app.post(V1+"/users/me/addresses")
def add_address(data:s.AddressIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    if data.is_default:
        db.query(m.Address).filter_by(user_id=user.user_id).update({"is_default":False})
    row=m.Address(user_id=user.user_id,**data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@app.put(V1+"/users/me/addresses/{address_id}")
def edit_address(address_id:int,data:s.AddressIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    row=db.query(m.Address).filter_by(address_id=address_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Address not found")
    for k,v in data.model_dump().items(): setattr(row,k,v)
    db.commit(); return row

@app.delete(V1+"/users/me/addresses/{address_id}")
def delete_address(address_id:int,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    row=db.query(m.Address).filter_by(address_id=address_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Address not found")
    db.delete(row); db.commit(); return {"message":"Address deleted"}

# 3. Restaurant discovery and search
@app.get(V1+"/home")
def home(db:Session=Depends(get_db)):
    return {"restaurants":db.query(m.Restaurant).filter_by(status="approved",is_open=True).limit(10).all(),
            "popular_items":db.query(m.MenuItem).filter_by(is_available=True).limit(10).all()}

@app.get(V1+"/restaurants")
def restaurants(q:str|None=None,cuisine:str|None=None,veg:bool|None=None,
                db:Session=Depends(get_db)):
    query=db.query(m.Restaurant).filter_by(status="approved")
    if q: query=query.filter(m.Restaurant.name.ilike(f"%{q}%"))
    if cuisine: query=query.filter(m.Restaurant.cuisine.ilike(f"%{cuisine}%"))
    return query.all()

@app.get(V1+"/search")
def search(q:str=Query(min_length=1),db:Session=Depends(get_db)):
    rests=db.query(m.Restaurant).filter(m.Restaurant.status=="approved",m.Restaurant.name.ilike(f"%{q}%")).all()
    items=db.query(m.MenuItem).filter(m.MenuItem.is_available==True,m.MenuItem.name.ilike(f"%{q}%")).all()
    return {"restaurants":rests,"items":items}

@app.get(V1+"/restaurants/{restaurant_id}")
def restaurant_detail(restaurant_id:int,db:Session=Depends(get_db)):
    row=db.query(m.Restaurant).filter_by(restaurant_id=restaurant_id,status="approved").first()
    if not row: raise HTTPException(404,"Restaurant not found")
    return row

# 4. Menu and item management
@app.get(V1+"/restaurants/{restaurant_id}/menu")
def menu(restaurant_id:int,db:Session=Depends(get_db)):
    return db.query(m.MenuItem).filter_by(restaurant_id=restaurant_id,is_available=True).all()

@app.get(V1+"/menu-items/{item_id}")
def item_detail(item_id:int,db:Session=Depends(get_db)):
    row=db.query(m.MenuItem).filter_by(item_id=item_id).first()
    if not row: raise HTTPException(404,"Item not found")
    return row

@app.post(V1+"/restaurant-portal/menu")
def create_menu(data:s.MenuItemIn,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    if not rest: raise HTTPException(404,"Create a restaurant profile first")
    row=m.MenuItem(restaurant_id=rest.restaurant_id,**data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@app.get(V1+"/restaurant-portal/menu")
def own_menu(user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    return [] if not rest else db.query(m.MenuItem).filter_by(restaurant_id=rest.restaurant_id).all()

@app.put(V1+"/restaurant-portal/menu/{item_id}")
def update_menu(item_id:int,data:s.MenuItemIn,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    row=db.query(m.MenuItem).join(m.Restaurant).filter(m.MenuItem.item_id==item_id,m.Restaurant.owner_id==user.user_id).first()
    if not row: raise HTTPException(404,"Menu item not found")
    for k,v in data.model_dump().items(): setattr(row,k,v)
    db.commit(); return row

@app.delete(V1+"/restaurant-portal/menu/{item_id}")
def remove_menu(item_id:int,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    row=db.query(m.MenuItem).join(m.Restaurant).filter(m.MenuItem.item_id==item_id,m.Restaurant.owner_id==user.user_id).first()
    if not row: raise HTTPException(404,"Menu item not found")
    row.is_available=False; db.commit(); return {"message":"Item archived"}

# 5. Cart and customization
@app.get(V1+"/cart")
def get_cart(user=Depends(allow("customer")),db:Session=Depends(get_db)):
    rows=db.query(m.CartItem,m.MenuItem).join(m.MenuItem,m.CartItem.item_id==m.MenuItem.item_id).filter(m.CartItem.user_id==user.user_id).all()
    items=[{"cart_item_id":c.cart_item_id,"item_id":i.item_id,"name":i.name,"quantity":c.quantity,
            "unit_price":float(i.price),"customization":c.customization,"subtotal":float(i.price)*c.quantity} for c,i in rows]
    return {"items":items,"subtotal":sum(x["subtotal"] for x in items)}

@app.post(V1+"/cart/items")
def add_cart(data:s.CartIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    item=db.query(m.MenuItem).filter_by(item_id=data.item_id,is_available=True).first()
    if not item: raise HTTPException(404,"Available menu item not found")
    row=db.query(m.CartItem).filter_by(user_id=user.user_id,item_id=data.item_id,customization=data.customization).first()
    if row: row.quantity+=data.quantity
    else: db.add(m.CartItem(user_id=user.user_id,**data.model_dump()))
    db.commit(); return get_cart(user,db)

@app.patch(V1+"/cart/items/{cart_item_id}")
def update_cart(cart_item_id:int,data:s.CartIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    row=db.query(m.CartItem).filter_by(cart_item_id=cart_item_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Cart item not found")
    row.quantity=data.quantity; row.customization=data.customization; db.commit(); return get_cart(user,db)

@app.delete(V1+"/cart/items/{cart_item_id}")
def remove_cart(cart_item_id:int,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    row=db.query(m.CartItem).filter_by(cart_item_id=cart_item_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Cart item not found")
    db.delete(row); db.commit(); return get_cart(user,db)

# 6. Checkout, offers and pricing
@app.post(V1+"/checkout/validate")
def validate_checkout(data:s.CheckoutIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    addr=db.query(m.Address).filter_by(address_id=data.address_id,user_id=user.user_id).first()
    if not addr: raise HTTPException(400,"Select a valid saved address")
    cart=get_cart(user,db)
    if not cart["items"]: raise HTTPException(400,"Cart is empty")
    subtotal=Decimal(str(cart["subtotal"]))
    delivery=Decimal("30.00"); packaging=Decimal("10.00"); tax=(subtotal*Decimal("0.05")).quantize(Decimal("0.01"))
    discount=Decimal("0.00")
    if data.promo_code:
        promo=db.query(m.Promotion).filter_by(code=data.promo_code.upper(),is_active=True).first()
        if promo:
            discount=(subtotal*promo.discount_value/100 if promo.discount_type=="percent" else promo.discount_value)
            discount=min(discount,subtotal)
    total=max(Decimal("0"),subtotal+delivery+packaging+tax+Decimal(str(data.tip))-discount)
    return {"subtotal":float(subtotal),"delivery_fee":float(delivery),"packaging_fee":float(packaging),
            "tax":float(tax),"discount":float(discount),"tip":data.tip,"total":float(total),"address":addr.address_text}

# 7 & 8. Payment and order management
@app.post(V1+"/orders")
def place_order(data:s.CheckoutIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    summary=validate_checkout(data,user,db)
    cart_rows=db.query(m.CartItem,m.MenuItem).join(m.MenuItem).filter(m.CartItem.user_id==user.user_id).all()
    restaurant_ids={i.restaurant_id for c,i in cart_rows}
    if len(restaurant_ids)!=1: raise HTTPException(400,"A cart must contain items from one restaurant")
    addr=db.query(m.Address).filter_by(address_id=data.address_id,user_id=user.user_id).first()
    order=m.Order(user_id=user.user_id,restaurant_id=next(iter(restaurant_ids)),
                  total_amount=summary["total"],delivery_address=addr.address_text,status="placed")
    try:
        db.add(order); db.flush()
        for c,i in cart_rows:
            if not i.is_available: raise HTTPException(400,f"{i.name} is unavailable")
            db.add(m.OrderItem(order_id=order.order_id,item_id=i.item_id,quantity=c.quantity,
                               unit_price=i.price,customization=c.customization))
        db.add(m.Payment(order_id=order.order_id,method=data.payment_method,amount=summary["total"],
                         status="pending" if data.payment_method!="COD" else "pending"))
        db.query(m.CartItem).filter_by(user_id=user.user_id).delete()
        notify(db,user.user_id,f"Your ShiftBite order #{order.order_id} has been placed.")
        db.commit(); db.refresh(order)
        return {"order_id":order.order_id,"status":order.status,"total":float(order.total_amount)}
    except:
        db.rollback(); raise

@app.get(V1+"/orders")
def my_orders(user=Depends(allow("customer")),db:Session=Depends(get_db)):
    return db.query(m.Order).filter_by(user_id=user.user_id).order_by(m.Order.created_at.desc()).all()

@app.get(V1+"/orders/{order_id}")
def order_detail(order_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.query(m.Order).filter_by(order_id=order_id).first()
    if not row: raise HTTPException(404,"Order not found")
    if user.role=="customer" and row.user_id!=user.user_id: raise HTTPException(403,"Forbidden")
    if user.role=="restaurant_owner":
        rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id,restaurant_id=row.restaurant_id).first()
        if not rest: raise HTTPException(403,"Forbidden")
    return {"order":row,"items":db.query(m.OrderItem).filter_by(order_id=order_id).all(),
            "payments":db.query(m.Payment).filter_by(order_id=order_id).all()}

@app.post(V1+"/orders/{order_id}/cancel")
def cancel_order(order_id:int,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    row=db.query(m.Order).filter_by(order_id=order_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Order not found")
    if row.status not in ("placed","accepted"): raise HTTPException(400,"Order can no longer be cancelled")
    row.status="cancelled"; db.commit(); notify(db,user.user_id,f"Order #{order_id} was cancelled."); db.commit()
    return {"status":row.status}

@app.get(V1+"/payments/{payment_id}")
def payment_status(payment_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    p=db.query(m.Payment).filter_by(payment_id=payment_id).first()
    if not p: raise HTTPException(404,"Payment not found")
    order=db.query(m.Order).filter_by(order_id=p.order_id).first()
    if user.role!="admin" and order.user_id!=user.user_id: raise HTTPException(403,"Forbidden")
    return p

@app.post(V1+"/payments/webhook")
def payment_webhook(payload:dict):
    # Production: verify provider signature, timestamp and replay protection before updating payment.
    return {"received":True,"note":"Configure and verify a real payment provider webhook before use."}

# 9. Delivery partner and dispatch
@app.post(V1+"/delivery-partners/me/register")
def register_delivery_partner(vehicle:str="",user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    existing=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    if existing: return existing
    row=m.DeliveryPartner(user_id=user.user_id,vehicle=vehicle); db.add(row); db.commit(); db.refresh(row); return row

@app.patch(V1+"/delivery-partners/me/availability")
def set_availability(data:s.AvailabilityIn,user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    if data.availability not in ("online","offline"): raise HTTPException(400,"Use online or offline")
    row=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Delivery profile not found")
    row.availability=data.availability; db.commit(); return row

@app.get(V1+"/delivery-partners/me/requests")
def delivery_requests(user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    partner=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    if not partner: raise HTTPException(404,"Delivery profile not found")
    return db.query(m.Delivery).filter(or_(m.Delivery.partner_id==partner.partner_id,m.Delivery.partner_id==None)).all()

@app.post(V1+"/admin/orders/{order_id}/assign")
def assign_delivery(order_id:int,data:s.DeliveryAssignIn,user=Depends(allow("admin")),db:Session=Depends(get_db)):
    order=db.query(m.Order).filter_by(order_id=order_id).first()
    partner=db.query(m.DeliveryPartner).filter_by(partner_id=data.partner_id,availability="online").first()
    if not order or not partner: raise HTTPException(404,"Order or online partner not found")
    delivery=m.Delivery(order_id=order_id,partner_id=partner.partner_id,status="assigned")
    db.add(delivery); order.status="ready_for_pickup"; db.commit(); db.refresh(delivery); return delivery

@app.post(V1+"/deliveries/{delivery_id}/accept")
def accept_delivery(delivery_id:int,user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    partner=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    row=db.query(m.Delivery).filter_by(delivery_id=delivery_id,partner_id=partner.partner_id).first() if partner else None
    if not row: raise HTTPException(404,"Delivery assignment not found")
    return {"message":"Delivery accepted","delivery_id":row.delivery_id}

@app.patch(V1+"/deliveries/{delivery_id}/status")
def delivery_status(delivery_id:int,data:s.StatusIn,user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    partner=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    row=db.query(m.Delivery).filter_by(delivery_id=delivery_id,partner_id=partner.partner_id).first() if partner else None
    allowed={"assigned":"arrived_restaurant","arrived_restaurant":"picked_up","picked_up":"on_the_way","on_the_way":"delivered"}
    if not row or allowed.get(row.status)!=data.status: raise HTTPException(400,"Invalid delivery or status transition")
    row.status=data.status
    order=db.query(m.Order).filter_by(order_id=row.order_id).first()
    order.status="delivered" if data.status=="delivered" else data.status
    if data.status=="delivered": row.delivered_at=datetime.now(timezone.utc)
    db.commit(); notify(db,order.user_id,f"Delivery update: {data.status}"); db.commit()
    return {"delivery_status":row.status,"order_status":order.status}

# 10. Tracking and notifications
@app.get(V1+"/orders/{order_id}/tracking")
def tracking(order_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    order=db.query(m.Order).filter_by(order_id=order_id).first()
    if not order: raise HTTPException(404,"Order not found")
    if user.role=="customer" and order.user_id!=user.user_id: raise HTTPException(403,"Forbidden")
    delivery=db.query(m.Delivery).filter_by(order_id=order_id).order_by(m.Delivery.delivery_id.desc()).first()
    return {"order_status":order.status,"delivery":delivery,"note":"GPS/map ETA requires configured provider integration."}

@app.patch(V1+"/deliveries/{delivery_id}/location")
def update_location(delivery_id:int,data:s.LocationIn,user=Depends(allow("delivery_partner")),db:Session=Depends(get_db)):
    partner=db.query(m.DeliveryPartner).filter_by(user_id=user.user_id).first()
    row=db.query(m.Delivery).filter_by(delivery_id=delivery_id,partner_id=partner.partner_id).first() if partner else None
    if not row: raise HTTPException(404,"Delivery not found")
    row.current_location=data.location; partner.current_location=data.location; db.commit()
    return {"message":"Latest location saved"}

@app.get(V1+"/notifications")
def notifications(user=Depends(current_user),db:Session=Depends(get_db)):
    return db.query(m.Notification).filter_by(user_id=user.user_id).order_by(m.Notification.created_at.desc()).all()

@app.patch(V1+"/notifications/{notification_id}/read")
def read_notification(notification_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.query(m.Notification).filter_by(notification_id=notification_id,user_id=user.user_id).first()
    if not row: raise HTTPException(404,"Notification not found")
    row.status="read"; db.commit(); return {"message":"Marked as read"}

# 11. Ratings, reviews and support
@app.post(V1+"/orders/{order_id}/reviews")
def create_review(order_id:int,data:s.ReviewIn,user=Depends(allow("customer")),db:Session=Depends(get_db)):
    order=db.query(m.Order).filter_by(order_id=order_id,user_id=user.user_id,status="delivered").first()
    if not order: raise HTTPException(400,"Only completed orders can be reviewed")
    if db.query(m.Review).filter_by(order_id=order_id,user_id=user.user_id).first(): raise HTTPException(409,"Review already submitted")
    row=m.Review(order_id=order_id,user_id=user.user_id,restaurant_id=order.restaurant_id,**data.model_dump())
    db.add(row); db.commit(); return {"message":"Review submitted"}

@app.post(V1+"/support/tickets")
def create_ticket(data:s.TicketIn,user=Depends(current_user),db:Session=Depends(get_db)):
    row=m.SupportTicket(user_id=user.user_id,**data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@app.get(V1+"/support/tickets")
def my_tickets(user=Depends(current_user),db:Session=Depends(get_db)):
    q=db.query(m.SupportTicket)
    if user.role!="admin": q=q.filter_by(user_id=user.user_id)
    return q.all()

# 12. Restaurant partner portal
@app.post(V1+"/restaurant-portal/profile")
def create_restaurant(data:s.RestaurantIn,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    row=m.Restaurant(owner_id=user.user_id,**data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@app.get(V1+"/restaurant-portal/dashboard")
def restaurant_dashboard(user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    if not rest: return {"message":"Create restaurant profile first"}
    orders=db.query(m.Order).filter_by(restaurant_id=rest.restaurant_id).all()
    return {"restaurant":rest.name,"total_orders":len(orders),
            "pending_orders":sum(o.status=="placed" for o in orders),
            "earnings":sum(float(o.total_amount) for o in orders if o.status=="delivered")}

@app.get(V1+"/restaurant-portal/orders")
def restaurant_orders(user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    return [] if not rest else db.query(m.Order).filter_by(restaurant_id=rest.restaurant_id).all()

@app.patch(V1+"/restaurant-portal/orders/{order_id}/decision")
def restaurant_decision(order_id:int,data:s.DecisionIn,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    order=db.query(m.Order).filter_by(order_id=order_id,restaurant_id=rest.restaurant_id if rest else -1).first()
    if not order or order.status!="placed": raise HTTPException(404,"Pending order not found")
    if data.decision not in ("accept","reject"): raise HTTPException(400,"Decision must be accept or reject")
    order.status="accepted" if data.decision=="accept" else "rejected"
    db.commit(); notify(db,order.user_id,f"Restaurant {data.decision}ed order #{order_id}"); db.commit()
    return {"status":order.status,"preparation_minutes":data.preparation_minutes}

@app.patch(V1+"/restaurant-portal/orders/{order_id}/status")
def restaurant_order_status(order_id:int,data:s.StatusIn,user=Depends(allow("restaurant_owner")),db:Session=Depends(get_db)):
    rest=db.query(m.Restaurant).filter_by(owner_id=user.user_id).first()
    order=db.query(m.Order).filter_by(order_id=order_id,restaurant_id=rest.restaurant_id if rest else -1).first()
    transitions={"accepted":["preparing"],"preparing":["ready_for_pickup"]}
    if not order or data.status not in transitions.get(order.status,[]): raise HTTPException(400,"Invalid order status transition")
    order.status=data.status; db.commit(); return {"status":order.status}

# 13. Admin console and analytics
@app.get(V1+"/admin/dashboard")
def admin_dashboard(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return {"users":db.query(m.User).count(),"restaurants":db.query(m.Restaurant).count(),
            "orders":db.query(m.Order).count(),"revenue":float(db.query(func.coalesce(func.sum(m.Order.total_amount),0)).filter(m.Order.status=="delivered").scalar())}

@app.get(V1+"/admin/users")
def admin_users(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return db.query(m.User).all()

@app.patch(V1+"/admin/users/{user_id}/status")
def admin_user_status(user_id:int,data:s.StatusIn,user=Depends(allow("admin")),db:Session=Depends(get_db)):
    row=db.query(m.User).filter_by(user_id=user_id).first()
    if not row: raise HTTPException(404,"User not found")
    if data.status not in ("active","suspended"): raise HTTPException(400,"Invalid account status")
    row.status=data.status; db.commit(); return {"status":row.status}

@app.get(V1+"/admin/restaurants")
def admin_restaurants(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return db.query(m.Restaurant).all()

@app.patch(V1+"/admin/restaurants/{restaurant_id}/status")
def admin_restaurant_status(restaurant_id:int,data:s.StatusIn,user=Depends(allow("admin")),db:Session=Depends(get_db)):
    row=db.query(m.Restaurant).filter_by(restaurant_id=restaurant_id).first()
    if not row: raise HTTPException(404,"Restaurant not found")
    if data.status not in ("approved","rejected","suspended"): raise HTTPException(400,"Invalid restaurant status")
    row.status=data.status; db.commit(); return {"status":row.status}

@app.get(V1+"/admin/delivery-partners")
def admin_delivery_partners(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return db.query(m.DeliveryPartner).all()

@app.get(V1+"/admin/orders")
def admin_orders(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return db.query(m.Order).all()

@app.patch(V1+"/admin/support/tickets/{ticket_id}/resolution")
def resolve_ticket(ticket_id:int,data:dict,user=Depends(allow("admin")),db:Session=Depends(get_db)):
    row=db.query(m.SupportTicket).filter_by(ticket_id=ticket_id).first()
    if not row: raise HTTPException(404,"Ticket not found")
    row.status=data.get("status","resolved"); row.resolution=data.get("resolution","")
    db.commit(); return {"status":row.status,"resolution":row.resolution}

@app.get(V1+"/admin/reports")
def reports(user=Depends(allow("admin")),db:Session=Depends(get_db)):
    return {"orders_by_status":dict(db.query(m.Order.status,func.count(m.Order.order_id)).group_by(m.Order.status).all()),
            "delivered_revenue":float(db.query(func.coalesce(func.sum(m.Order.total_amount),0)).filter(m.Order.status=="delivered").scalar())}
