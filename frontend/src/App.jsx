import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight, Utensils, ShoppingBag, Bike, Store, ShieldCheck,
  Search, MapPin, Clock, Star, Menu, X, LogOut, LayoutDashboard,
  Package, Users, TrendingUp, ChefHat, Plus, RefreshCw, Eye, EyeOff,
  Sparkles, CircleUserRound, ChevronRight, Minus, Trash2, CreditCard,
  CheckCircle2, Truck, ClipboardList, Headset, UserCog, Check, Ban
} from "lucide-react";

import api, {
  loginUser,
  registerCustomer,
  getRestaurants,
  getMyOrders,
  getRestaurantDashboard,
  getRestaurantOrders,
  getRestaurantMenu,
  getDeliveryRequests,
  setDeliveryAvailability,
  acceptDelivery,
  registerRestaurant,
  registerDeliveryPartner,
  updateDeliveryStatus,
  updateDeliveryLocation,
  getAdminDashboard,
  getAdminUsers,
  getAdminRestaurants,
  checkBackend
} from "./services/api";

import "./App.css";

const roles = [
  { id: "customer", label: "Customer", icon: ShoppingBag },
  { id: "restaurant_owner", label: "Restaurant", icon: Store },
  { id: "delivery_partner", label: "Delivery Partner", icon: Bike },
  { id: "admin", label: "Administrator", icon: ShieldCheck }
];

const money = (value) =>
  `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  })}`;

const getArray = (data, keys = []) => {
  if (Array.isArray(data)) return data;
  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key];
  }
  return [];
};

function Brand({ small = false }) {
  return (
    <a className={`brand ${small ? "brand-small" : ""}`} href="#home">
      <span className="brand-icon"><Utensils size={small ? 18 : 21} /></span>
      <span>SHIFT<span className="brand-accent">BITE</span></span>
    </a>
  );
}

function StatCard({ icon: Icon, label, value, note }) {
  return (
    <article className="stat-card">
      <span className="stat-icon"><Icon size={20} /></span>
      <p>{label}</p>
      <strong>{value ?? "—"}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <Package size={26} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}


function CustomerDiscovery({ restaurants = [], onCartUpdated }) {
  const [term, setTerm] = useState("");
  const [selected, setSelected] = useState(null);
  const [menuItems, setMenuItems] = useState([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [menuError, setMenuError] = useState("");
  const [addingId, setAddingId] = useState(null);
  const [message, setMessage] = useState("");

  const visibleRestaurants = restaurants.filter((r) =>
    [r.name, r.cuisine, r.address].filter(Boolean).join(" ").toLowerCase().includes(term.toLowerCase())
  );

  const openMenu = async (restaurant) => {
    setSelected(restaurant);
    setMenuItems([]);
    setMenuError("");
    setMessage("");
    setMenuLoading(true);
    try {
      const { data } = await api.get(`/restaurants/${restaurant.restaurant_id}/menu`);
      setMenuItems(getArray(data, ["items", "menu", "menu_items"]));
    } catch (err) {
      setMenuError(err.response?.data?.detail || "We couldn't load this menu. Please try again.");
    } finally {
      setMenuLoading(false);
    }
  };

  const addItem = async (item) => {
    setAddingId(item.item_id);
    setMessage("");
    try {
      await api.post("/cart/items", { item_id: item.item_id, quantity: 1, customization: null });
      setMessage(`${item.name} added to your cart.`);
      onCartUpdated?.();
    } catch (err) {
      setMenuError(err.response?.data?.detail || "Unable to add this item. Please try again.");
    } finally {
      setAddingId(null);
    }
  };

  return (
    <section className="customer-discovery">
      <div className="customer-discovery-head">
        <div><p className="eyebrow">FRESH PICKS, JUST FOR YOU</p><h2>Find your next <span>favourite.</span></h2><p>Explore approved restaurants, discover their menus and add something delicious to your cart.</p></div>
        <div className="customer-search"><Search size={17}/><input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Search food, cuisine or restaurant" /></div>
      </div>
      {visibleRestaurants.length ? (
        <div className="customer-restaurant-grid">
          {visibleRestaurants.map((restaurant, index) => (
            <article className="customer-restaurant-card" key={restaurant.restaurant_id || index}>
              <div className="customer-restaurant-image">
                <img src={restaurant.image_url || [
                  "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80",
                  "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=900&q=80",
                  "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=900&q=80"
                ][index % 3]} alt={restaurant.name || "Restaurant"}/>
                <span>{restaurant.cuisine || "CURATED DINING"}</span>
              </div>
              <div className="customer-restaurant-info">
                <div className="customer-restaurant-title"><h3>{restaurant.name}</h3><span><Star size={13}/> {restaurant.rating || "New"}</span></div>
                <p>{restaurant.address || "Freshly prepared favourites, ready to discover."}</p>
                <button className="gold-button customer-menu-button" onClick={() => openMenu(restaurant)}>Explore menu <ArrowRight size={15}/></button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="customer-empty">
          <span className="customer-empty-icon"><ChefHat size={25}/></span>
          <h3>{term ? "No matching restaurants" : "Your food journey starts here"}</h3>
          <p>{term ? "Try another restaurant name or cuisine." : "No approved restaurants are available yet. Once the admin approves a restaurant and its owner adds menu items, the food will appear here."}</p>
        </div>
      )}

      {selected && (
        <div className="customer-menu-backdrop" onMouseDown={() => setSelected(null)}>
          <section className="customer-menu-modal" onMouseDown={(e) => e.stopPropagation()}>
            <div className="customer-menu-top">
              <div><p className="eyebrow">EXPLORE THE MENU</p><h2>{selected.name}</h2><p>{selected.cuisine || "Made fresh, made for you"}</p></div>
              <button className="icon-button" onClick={() => setSelected(null)} aria-label="Close menu"><X size={20}/></button>
            </div>
            {menuLoading && <div className="state-panel"><RefreshCw className="spin"/> Loading menu...</div>}
            {menuError && <p className="form-error">{menuError}</p>}
            {message && <p className="form-notice">{message}</p>}
            {!menuLoading && menuItems.length > 0 && (
              <div className="customer-menu-list">
                {menuItems.map((item) => (
                  <article className="customer-menu-item" key={item.item_id}>
                    {item.image_url ? <img src={item.image_url} alt={item.name}/> : <div className="menu-item-placeholder"><Utensils size={22}/></div>}
                    <div className="customer-menu-item-copy"><h3>{item.name}</h3><p>{item.description || item.category || "Prepared fresh by the restaurant."}</p><strong>{money(item.price)}</strong></div>
                    <button className="menu-add-button" disabled={addingId === item.item_id || item.is_available === false} onClick={() => addItem(item)}>{addingId === item.item_id ? "Adding..." : item.is_available === false ? "Unavailable" : <><Plus size={15}/> Add</>}</button>
                  </article>
                ))}
              </div>
            )}
            {!menuLoading && !menuError && menuItems.length === 0 && <EmptyState title="Menu coming soon" description="This restaurant has not added available food items yet."/>}
          </section>
        </div>
      )}
    </section>
  );
}


function CustomerCommerce({ orders = [], onRefresh }) {
  const [cart, setCart] = useState({ items: [], subtotal: 0 });
  const [addresses, setAddresses] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash_on_delivery");
  const [tip, setTip] = useState("0");
  const [promoCode, setPromoCode] = useState("");
  const [summary, setSummary] = useState(null);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [addressFormOpen, setAddressFormOpen] = useState(false);
  const [addressForm, setAddressForm] = useState({
    label: "Home", address_text: "", latitude: "", longitude: "", is_default: true
  });
  const [trackingOrder, setTrackingOrder] = useState(null);
  const [trackingInfo, setTrackingInfo] = useState(null);
  const [paymentInfo, setPaymentInfo] = useState(null);

  const loadCartAndAddresses = async () => {
    try {
      const [cartResponse, addressResponse] = await Promise.all([
        api.get("/cart"),
        api.get("/users/me/addresses")
      ]);
      const nextCart = cartResponse.data || { items: [], subtotal: 0 };
      const nextAddresses = getArray(addressResponse.data, ["addresses", "items"]);
      setCart(nextCart);
      setAddresses(nextAddresses);
      const defaultAddress = nextAddresses.find((a) => a.is_default) || nextAddresses[0];
      if (defaultAddress && !selectedAddress) setSelectedAddress(String(defaultAddress.address_id));
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load your cart or saved addresses.");
    }
  };

  useEffect(() => {
    loadCartAndAddresses();
  }, []);

  const changeQuantity = async (item, quantity) => {
    if (quantity < 1) return;
    setBusy(true);
    setError("");
    try {
      const { data } = await api.patch(`/cart/items/${item.cart_item_id}`, {
        item_id: item.item_id, quantity, customization: item.customization ?? null
      });
      setCart(data || { items: [], subtotal: 0 });
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to update item quantity.");
    } finally {
      setBusy(false);
    }
  };

  const removeItem = async (item) => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.delete(`/cart/items/${item.cart_item_id}`);
      setCart(data || { items: [], subtotal: 0 });
      setSummary(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to remove this item.");
    } finally {
      setBusy(false);
    }
  };

  const saveAddress = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/users/me/addresses", {
        ...addressForm,
        latitude: addressForm.latitude || null,
        longitude: addressForm.longitude || null
      });
      const next = [...addresses, data];
      setAddresses(next);
      setSelectedAddress(String(data.address_id));
      setAddressFormOpen(false);
      setAddressForm({ label: "Home", address_text: "", latitude: "", longitude: "", is_default: true });
      setNotice("Delivery address saved.");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to save this address.");
    } finally {
      setBusy(false);
    }
  };

  const validateOrder = async () => {
    if (!cart.items?.length) {
      setError("Your cart is empty. Add food from a restaurant menu first.");
      return;
    }
    if (!selectedAddress) {
      setError("Please add or select a delivery address.");
      setAddressFormOpen(true);
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        address_id: Number(selectedAddress),
        payment_method: paymentMethod,
        promo_code: promoCode.trim() || null,
        tip: Number(tip || 0)
      };
      const { data } = await api.post("/checkout/validate", payload);
      setSummary(data);
      setCheckoutOpen(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Checkout validation failed. Please review your cart and address.");
    } finally {
      setBusy(false);
    }
  };

  const placeCustomerOrder = async () => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        address_id: Number(selectedAddress),
        payment_method: paymentMethod,
        promo_code: promoCode.trim() || null,
        tip: Number(tip || 0)
      };
      const { data } = await api.post("/orders", payload);
      setCheckoutOpen(false);
      setSummary(null);
      setNotice(`Order #${data.order_id} placed successfully. Payment is recorded as pending until a payment provider is connected or the selected offline method is settled.`);
      await loadCartAndAddresses();
      await onRefresh?.();
    } catch (err) {
      setError(err.response?.data?.detail || "We couldn't place your order. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const showTracking = async (order) => {
    setTrackingOrder(order);
    setTrackingInfo(null);
    setPaymentInfo(null);
    setError("");
    try {
      const [trackingResponse, detailResponse] = await Promise.all([
        api.get(`/orders/${order.order_id}/tracking`),
        api.get(`/orders/${order.order_id}`)
      ]);
      setTrackingInfo(trackingResponse.data);
      const payments = detailResponse.data?.payments || [];
      setPaymentInfo(payments[0] || null);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load order tracking right now.");
    }
  };

  const itemCount = (cart.items || []).reduce((sum, item) => sum + Number(item.quantity || 0), 0);

  return (
    <section className="customer-commerce">
      <div className="customer-commerce-heading">
        <div><p className="eyebrow">YOUR ORDER, YOUR WAY</p><h2>Cart & <span>checkout</span></h2><p>Review your favourites, choose a delivery address and confirm your order.</p></div>
        <div className="customer-cart-count"><ShoppingBag size={19}/><strong>{itemCount}</strong><small>items in cart</small></div>
      </div>

      {error && <div className="customer-commerce-alert error">{error}</div>}
      {notice && <div className="customer-commerce-alert success"><CheckCircle2 size={17}/>{notice}</div>}

      <div className="customer-commerce-grid">
        <div className="customer-cart-panel">
          <div className="panel-heading"><h3>Your cart</h3><button className="text-button" onClick={loadCartAndAddresses}>Refresh cart <RefreshCw size={14}/></button></div>
          {cart.items?.length ? (
            <div className="customer-cart-items">
              {cart.items.map((item) => (
                <article className="customer-cart-item" key={item.cart_item_id}>
                  <div className="customer-cart-item-icon"><Utensils size={20}/></div>
                  <div className="customer-cart-item-copy"><h4>{item.name}</h4><p>{money(item.unit_price)} each</p><strong>{money(item.subtotal ?? item.unit_price * item.quantity)}</strong></div>
                  <div className="customer-quantity-control">
                    <button disabled={busy || item.quantity <= 1} onClick={() => changeQuantity(item, item.quantity - 1)} aria-label="Decrease quantity"><Minus size={13}/></button>
                    <span>{item.quantity}</span>
                    <button disabled={busy || item.quantity >= 50} onClick={() => changeQuantity(item, item.quantity + 1)} aria-label="Increase quantity"><Plus size={13}/></button>
                  </div>
                  <button className="customer-remove-item" disabled={busy} onClick={() => removeItem(item)} aria-label={`Remove ${item.name}`}><Trash2 size={16}/></button>
                </article>
              ))}
            </div>
          ) : (
            <div className="customer-cart-empty"><ShoppingBag size={27}/><h3>Your cart is waiting</h3><p>Explore a restaurant menu and add your favourite dishes. Your selected items will appear here.</p></div>
          )}
        </div>

        <aside className="customer-summary-panel">
          <p className="eyebrow">ORDER SUMMARY</p>
          <h3>Good food is closer.</h3>
          <div className="customer-summary-line"><span>Items ({itemCount})</span><strong>{money(cart.subtotal)}</strong></div>
          <div className="customer-summary-line"><span>Delivery & taxes</span><span>Calculated at checkout</span></div>
          <div className="customer-summary-total"><span>Cart subtotal</span><strong>{money(cart.subtotal)}</strong></div>
          <button className="gold-button customer-checkout-button" disabled={!cart.items?.length || busy} onClick={() => { setCheckoutOpen(true); setSummary(null); setError(""); }}>Continue to checkout <ArrowRight size={16}/></button>
        </aside>
      </div>

      {checkoutOpen && (
        <div className="customer-checkout-panel">
          <div className="panel-heading"><div><p className="eyebrow">SECURE CHECKOUT</p><h3>Delivery & payment details</h3></div><button className="text-button" onClick={() => setCheckoutOpen(false)}>Close <X size={15}/></button></div>
          <div className="customer-checkout-grid">
            <div className="customer-checkout-fields">
              <label htmlFor="customer-address">Delivery address</label>
              <select id="customer-address" value={selectedAddress} onChange={(e) => setSelectedAddress(e.target.value)}>
                <option value="">Select a saved address</option>
                {addresses.map((address) => <option key={address.address_id} value={address.address_id}>{address.label || "Address"} — {address.address_text}</option>)}
              </select>
              <button className="text-button customer-add-address-toggle" onClick={() => setAddressFormOpen(!addressFormOpen)}>{addressFormOpen ? "Hide address form" : "+ Add a delivery address"}</button>
              {addressFormOpen && (
                <form className="customer-address-form" onSubmit={saveAddress}>
                  <label htmlFor="address-label">Label</label>
                  <input id="address-label" value={addressForm.label} onChange={(e) => setAddressForm({...addressForm, label:e.target.value})} placeholder="Home, Work..." required/>
                  <label htmlFor="address-text">Full delivery address</label>
                  <textarea id="address-text" value={addressForm.address_text} onChange={(e) => setAddressForm({...addressForm, address_text:e.target.value})} placeholder="House number, street, area, city, PIN code" required/>
                  <button className="gold-button" disabled={busy} type="submit">Save address</button>
                </form>
              )}
              <label htmlFor="customer-payment">Payment method</label>
              <select id="customer-payment" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                <option value="cash_on_delivery">Cash on delivery</option>
                <option value="upi">UPI (recorded; gateway not connected)</option>
                <option value="card">Card (recorded; gateway not connected)</option>
              </select>
              <label htmlFor="customer-tip">Delivery partner tip (₹)</label>
              <input id="customer-tip" type="number" min="0" max="500" step="5" value={tip} onChange={(e) => setTip(e.target.value)}/>
              <label htmlFor="customer-promo">Promo code (optional)</label>
              <input id="customer-promo" value={promoCode} onChange={(e) => setPromoCode(e.target.value)} placeholder="Enter promo code"/>
              <button className="gold-button customer-checkout-button" disabled={busy} onClick={validateOrder}>{busy ? "Checking..." : "Review order total"} <ArrowRight size={15}/></button>
            </div>
            <div className="customer-checkout-review">
              <h4>Order total</h4>
              {summary ? (
                <>
                  {[
                    ["Subtotal", summary.subtotal], ["Delivery fee", summary.delivery_fee],
                    ["Packaging", summary.packaging_fee], ["Tax", summary.tax],
                    ["Discount", -Number(summary.discount || 0)], ["Tip", summary.tip]
                  ].map(([label, value]) => <div className="customer-summary-line" key={label}><span>{label}</span><strong>{money(value)}</strong></div>)}
                  <div className="customer-summary-total"><span>Total payable</span><strong>{money(summary.total)}</strong></div>
                  <p className="customer-payment-note"><CreditCard size={15}/> Payment gateway is not connected yet. The selected method and pending payment status will be saved with your order.</p>
                  <button className="gold-button customer-checkout-button" disabled={busy} onClick={placeCustomerOrder}>{busy ? "Placing order..." : "Place order"} <CheckCircle2 size={16}/></button>
                </>
              ) : <p className="customer-muted">Choose your address and payment method, then review the server-calculated total before placing your order.</p>}
            </div>
          </div>
        </div>
      )}

      <section className="customer-tracking-panel">
        <div className="panel-heading"><div><p className="eyebrow">AFTER YOU ORDER</p><h3>Order tracking & payment status</h3></div><Truck size={21}/></div>
        {orders.length ? (
          <div className="customer-order-tracking-list">
            {orders.slice(0, 5).map((order) => (
              <article className="customer-order-row" key={order.order_id}>
                <div><strong>Order #{order.order_id}</strong><small>{formatDate(order.created_at)} · {money(order.total_amount)}</small></div>
                <StatusPill value={order.status}/>
                <button className="outline-button" onClick={() => showTracking(order)}>Track order <ArrowRight size={14}/></button>
              </article>
            ))}
          </div>
        ) : <p className="customer-muted">Your order progress will appear here after checkout.</p>}
        {trackingOrder && (
          <div className="customer-tracking-detail">
            <div className="panel-heading"><h4>Order #{trackingOrder.order_id}</h4><button className="text-button" onClick={() => setTrackingOrder(null)}>Close</button></div>
            <div className="customer-tracking-stages">
              {["placed", "accepted", "preparing", "ready_for_pickup", "picked_up", "delivered"].map((stage) => {
                const current = String(trackingInfo?.order_status || trackingOrder.status || "").toLowerCase();
                const stages = ["placed", "accepted", "preparing", "ready_for_pickup", "picked_up", "delivered"];
                const active = stages.indexOf(current) >= stages.indexOf(stage) && stages.indexOf(current) >= 0;
                return <span className={active ? "tracking-stage active" : "tracking-stage"} key={stage}><i/>{stage.replaceAll("_", " ")}</span>;
              })}
            </div>
            <div className="customer-summary-line"><span>Payment method</span><strong>{paymentInfo?.method || "Not available"}</strong></div>
            <div className="customer-summary-line"><span>Payment status</span><StatusPill value={paymentInfo?.status || "pending"}/></div>
            {trackingInfo?.delivery?.current_location && <p className="customer-muted">Latest delivery location: {trackingInfo.delivery.current_location}</p>}
            {trackingInfo?.note && <p className="customer-muted">{trackingInfo.note}</p>}
          </div>
        )}
      </section>
    </section>
  );
}

function AdminControlCenter({ data, page, onRefresh }) {
  const [busyKey, setBusyKey] = useState("");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [partnerChoices, setPartnerChoices] = useState({});
  const users = data.users || [];
  const restaurants = data.restaurants || [];
  const orders = data.orders || [];
  const partners = data.deliveryPartners || [];
  const tickets = data.tickets || [];
  const onlinePartners = partners.filter((p) => p.availability === "online");

  const runAction = async (key, action, successMessage) => {
    setBusyKey(key); setError(""); setFeedback("");
    try { await action(); setFeedback(successMessage); await onRefresh?.(); }
    catch (err) { setError(err.response?.data?.detail || "This action could not be completed."); }
    finally { setBusyKey(""); }
  };

  const setUserStatus = (user, status) => runAction(`user-${user.user_id}`,
    () => api.patch(`/admin/users/${user.user_id}/status`, { status }),
    `${user.name}'s account is now ${status}.`);

  const restaurantDecision = (restaurant, decision) => runAction(`restaurant-${restaurant.restaurant_id}`,
    () => api.post(`/admin/restaurants/${restaurant.restaurant_id}/${decision}`),
    `${restaurant.name} was ${decision === "approve" ? "approved" : "rejected"}.`);

  const assignPartner = (order) => {
    const partnerId = Number(partnerChoices[order.order_id]);
    if (!partnerId) { setError("Choose an online delivery partner first."); return; }
    runAction(`order-${order.order_id}`,
      () => api.post(`/admin/orders/${order.order_id}/assign`, { partner_id: partnerId }),
      `A delivery partner was assigned to order #${order.order_id}.`);
  };

  const updateTicket = (ticket, status) => runAction(`ticket-${ticket.ticket_id}`,
    () => api.patch(`/admin/support/tickets/${ticket.ticket_id}`, { status }),
    `Support ticket #${ticket.ticket_id} was updated.`);

  return (
    <section className="admin-control-center">
      {feedback && <div className="admin-feedback success"><CheckCircle2 size={16}/>{feedback}</div>}
      {error && <div className="admin-feedback error">{error}</div>}
      {page === "users" && <section className="data-panel"><div className="panel-heading"><h3><UserCog size={18}/> User management</h3><span>{users.length} accounts</span></div>
        {users.length ? <DataTable rows={users} columns={[
          ["Name", (r) => r.name || "—"], ["Email", (r) => r.email || "—"],
          ["Role", (r) => String(r.role || "—").replaceAll("_", " ")],
          ["Status", (r) => <StatusPill value={r.status || "active"}/>],
          ["Account action", (r) => r.role === "admin" ? <span className="customer-muted">Protected</span> : <div className="admin-actions">{(r.status || "active") === "active" ? <button className="admin-action danger" disabled={!!busyKey} onClick={() => setUserStatus(r, "inactive")}>{busyKey === `user-${r.user_id}` ? "Saving..." : "Deactivate"}</button> : <button className="admin-action" disabled={!!busyKey} onClick={() => setUserStatus(r, "active")}>Activate</button>}{r.status !== "suspended" && <button className="admin-action danger" disabled={!!busyKey} onClick={() => setUserStatus(r, "suspended")}>Suspend</button>}</div>]
        ]}/> : <EmptyState title="No users found" description="Registered accounts will appear here."/>}
      </section>}

      {page === "restaurants-admin" && <section className="data-panel"><div className="panel-heading"><h3><Store size={18}/> Restaurant applications</h3><span>{restaurants.length} restaurants</span></div>
        {restaurants.length ? <DataTable rows={restaurants} columns={[
          ["Restaurant", (r) => r.name || "—"], ["Cuisine", (r) => r.cuisine || "—"],
          ["Status", (r) => <StatusPill value={r.status}/>], ["Address", (r) => r.address || "—"],
          ["Decision", (r) => r.status === "pending" ? <div className="admin-actions"><button className="admin-action" disabled={!!busyKey} onClick={() => restaurantDecision(r, "approve")}>{busyKey === `restaurant-${r.restaurant_id}` ? "Saving..." : <><Check size={13}/> Approve</>}</button><button className="admin-action danger" disabled={!!busyKey} onClick={() => restaurantDecision(r, "reject")}><Ban size={13}/> Reject</button></div> : <span className="customer-muted">Reviewed</span>]
        ]}/> : <EmptyState title="No restaurant applications" description="New restaurant registrations will appear here."/>}
      </section>}

      {page === "orders-admin" && <section className="data-panel"><div className="panel-heading"><h3><ClipboardList size={18}/> Order monitoring</h3><span>{orders.length} orders</span></div>
        {orders.length ? <DataTable rows={orders} columns={[
          ["Order", (r) => `#${r.order_id}`], ["Customer ID", (r) => r.user_id ?? "—"],
          ["Restaurant ID", (r) => r.restaurant_id ?? "—"], ["Amount", (r) => money(r.total_amount)],
          ["Status", (r) => <StatusPill value={r.status}/>],
          ["Delivery assignment", (r) => r.status === "ready_for_pickup" ? <div className="admin-assign"><select aria-label={`Delivery partner for order ${r.order_id}`} value={partnerChoices[r.order_id] || ""} onChange={(e) => setPartnerChoices((old) => ({...old, [r.order_id]: e.target.value}))}><option value="">Choose online partner</option>{onlinePartners.map((p) => <option key={p.partner_id} value={p.partner_id}>Partner #{p.partner_id} · User #{p.user_id}</option>)}</select><button className="admin-action" disabled={!!busyKey || !onlinePartners.length} onClick={() => assignPartner(r)}>Assign</button></div> : <span className="customer-muted">{r.status === "delivered" ? "Completed" : "Waiting for ready"}</span>]
        ]}/> : <EmptyState title="No orders yet" description="Customer orders will appear here."/>}
        {!onlinePartners.length && <p className="admin-hint">No delivery partners are currently online. Assignment becomes available when a partner is online.</p>}
      </section>}

      {page === "delivery-admin" && <section className="data-panel"><div className="panel-heading"><h3><Bike size={18}/> Delivery partners</h3><span>{partners.length} partners</span></div>
        {partners.length ? <DataTable rows={partners} columns={[["Partner ID", (r) => `#${r.partner_id}`],["User ID", (r) => r.user_id ?? "—"],["Vehicle", (r) => r.vehicle || "—"],["Availability", (r) => <StatusPill value={r.availability}/>],["Location", (r) => r.current_location || "Not shared"]]}/> : <EmptyState title="No delivery partners" description="Delivery partner registrations will appear here."/>}
      </section>}

      {page === "support-admin" && <section className="data-panel"><div className="panel-heading"><h3><Headset size={18}/> Customer support</h3><span>{tickets.length} tickets</span></div>
        {tickets.length ? <DataTable rows={tickets} columns={[["Ticket", (r) => `#${r.ticket_id}`],["User ID", (r) => r.user_id ?? "—"],["Order", (r) => r.order_id ? `#${r.order_id}` : "—"],["Subject", (r) => r.subject || "—"],["Status", (r) => <StatusPill value={r.status}/>],["Update", (r) => <select className="admin-status-select" disabled={!!busyKey} value={r.status} onChange={(e) => updateTicket(r, e.target.value)}><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option><option value="closed">Closed</option></select>]]}/> : <EmptyState title="No support tickets" description="Customer support requests will appear here."/>}
      </section>}
    </section>
  );
}

function DashboardContent({ role, data, page, onNavigate, onRefresh, restaurants, onCartUpdated }) {
  const [deliveryBusy, setDeliveryBusy] = useState(false);
  const [menuFormOpen, setMenuFormOpen] = useState(false);
  const [menuSaving, setMenuSaving] = useState(false);
  const [menuEditingId, setMenuEditingId] = useState(null);
  const [menuFeedback, setMenuFeedback] = useState("");
  const [menuError, setMenuError] = useState("");
  const emptyMenuForm = {
    name: "", description: "", category: "Main Course",
    price: "", is_veg: true, is_available: true, image_url: ""
  };
  const [menuForm, setMenuForm] = useState(emptyMenuForm);

  const saveMenuItem = async (event) => {
    event.preventDefault();
    setMenuSaving(true);
    setMenuFeedback("");
    setMenuError("");
    try {
      const payload = {
        name: menuForm.name.trim(),
        description: menuForm.description.trim() || null,
        category: menuForm.category.trim() || null,
        price: Number(menuForm.price),
        is_veg: Boolean(menuForm.is_veg),
        is_available: Boolean(menuForm.is_available),
        image_url: menuForm.image_url.trim() || null
      };
      if (!payload.name || !Number.isFinite(payload.price) || payload.price <= 0) {
        throw new Error("Enter a food name and a price greater than zero.");
      }
      if (menuEditingId) {
        await api.put(`/restaurant-portal/menu/${menuEditingId}`, payload);
        setMenuFeedback("Menu item updated successfully.");
      } else {
        await api.post("/restaurant-portal/menu", payload);
        setMenuFeedback("Food item added successfully.");
      }
      setMenuForm(emptyMenuForm);
      setMenuEditingId(null);
      setMenuFormOpen(false);
      await onRefresh?.();
    } catch (err) {
      setMenuError(err.response?.data?.detail || err.message || "Could not save menu item.");
    } finally {
      setMenuSaving(false);
    }
  };

  const editMenuItem = (item) => {
    setMenuEditingId(item.item_id);
    setMenuForm({
      name: item.name || "",
      description: item.description || "",
      category: item.category || "Main Course",
      price: item.price ?? "",
      is_veg: item.is_veg !== false,
      is_available: item.is_available !== false,
      image_url: item.image_url || ""
    });
    setMenuFormOpen(true);
    setMenuFeedback("");
    setMenuError("");
  };

  const archiveMenuItem = async (item) => {
    if (!window.confirm(`Remove ${item.name || "this item"} from your menu?`)) return;
    setMenuSaving(true);
    setMenuFeedback("");
    setMenuError("");
    try {
      await api.delete(`/restaurant-portal/menu/${item.item_id}`);
      setMenuFeedback("Menu item removed from customer view.");
      await onRefresh?.();
    } catch (err) {
      setMenuError(err.response?.data?.detail || err.message || "Could not remove menu item.");
    } finally {
      setMenuSaving(false);
    }
  };

  const toggleMenuAvailability = async (item) => {
    setMenuSaving(true);
    setMenuFeedback("");
    setMenuError("");
    try {
      await api.put(`/restaurant-portal/menu/${item.item_id}`, {
        name: item.name,
        description: item.description || null,
        category: item.category || null,
        price: Number(item.price),
        is_veg: item.is_veg !== false,
        is_available: item.is_available === false,
        image_url: item.image_url || null
      });
      setMenuFeedback(`Availability updated for ${item.name}.`);
      await onRefresh?.();
    } catch (err) {
      setMenuError(err.response?.data?.detail || err.message || "Could not update availability.");
    } finally {
      setMenuSaving(false);
    }
  };
  const [deliveryFeedback, setDeliveryFeedback] = useState("");
  const [deliveryError, setDeliveryError] = useState("");
  const [locationDraft, setLocationDraft] = useState("");

  const runDeliveryAction = async (action, successMessage) => {
    setDeliveryBusy(true);
    setDeliveryFeedback("");
    setDeliveryError("");
    try {
      await action();
      setDeliveryFeedback(successMessage);
      await onRefresh?.();
    } catch (err) {
      setDeliveryError(err.response?.data?.detail || err.message || "Delivery action failed. Please try again.");
    } finally {
      setDeliveryBusy(false);
    }
  };
  if (role === "customer") {
    const orders = data.orders || [];
    return (
      <>
        <div className="dashboard-heading">
          <div><p className="eyebrow">YOUR ACTIVITY</p><h2>Your dining, at a glance</h2></div>
          <button className="outline-button" onClick={onRefresh}><RefreshCw size={15} /> Refresh</button>
        </div>
        <div className="stats-grid">
          <StatCard icon={Package} label="Total orders" value={orders.length} />
          <StatCard icon={ShoppingBag} label="Cart items" value={data.cart?.items?.length ?? data.cart?.total_items ?? 0} />
          <StatCard icon={TrendingUp} label="Recent activity" value={orders.length ? "Active" : "New"} />
        </div>
        <CustomerDiscovery restaurants={restaurants} onCartUpdated={onCartUpdated} />
        <CustomerCommerce orders={orders} onRefresh={onCartUpdated} />
        <section className="data-panel">
          <div className="panel-heading"><h3>Recent orders</h3><button className="text-button" onClick={() => onNavigate("orders")}>View all <ChevronRight size={15} /></button></div>
          {orders.length ? <DataTable rows={orders.slice(0, 5)} columns={[
            ["Order", (r) => `#${r.order_id ?? r.id ?? "—"}`],
            ["Date", (r) => formatDate(r.created_at)],
            ["Status", (r) => <StatusPill value={r.status} />],
            ["Total", (r) => money(r.total_amount ?? r.total)]
          ]} /> : <EmptyState title="No orders yet" description="Your orders will appear here after your first checkout." />}
        </section>
        {page === "orders" && <section className="data-panel"><h3>All orders</h3>{orders.length ? <DataTable rows={orders} columns={[
          ["Order", (r) => `#${r.order_id ?? r.id ?? "—"}`],
          ["Date", (r) => formatDate(r.created_at)],
          ["Status", (r) => <StatusPill value={r.status} />],
          ["Total", (r) => money(r.total_amount ?? r.total)]
        ]} /> : <EmptyState title="No orders found" description="Placed orders will be listed here." />}</section>}
      </>
    );
  }

  if (role === "restaurant_owner") {
    const overview = data.overview || {};
    const orders = data.orders || [];
    const menu = data.menu || [];
    return (
      <>
        <div className="dashboard-heading">
          <div><p className="eyebrow">RESTAURANT OPERATIONS</p><h2>Restaurant overview</h2></div>
          <button className="outline-button" onClick={onRefresh}><RefreshCw size={15} /> Refresh</button>
        </div>
        <div className="stats-grid">
          <StatCard icon={ShoppingBag} label="Total orders" value={overview.total_orders ?? orders.length} />
          <StatCard icon={Clock} label="Pending orders" value={overview.pending_orders ?? orders.filter((o) => o.status === "pending").length} />
          <StatCard icon={ChefHat} label="Menu items" value={overview.total_menu_items ?? menu.length} />
          <StatCard icon={TrendingUp} label="Revenue" value={money(overview.total_revenue)} />
        </div>
        {page === "menu" ? (
          <section className="data-panel">
            <div className="panel-heading">
              <div><h3>Menu management</h3><p className="delivery-subtitle">Add and manage the food customers can order.</p></div>
              <button className="admin-action" onClick={() => {
                setMenuEditingId(null);
                setMenuForm(emptyMenuForm);
                setMenuFormOpen((open) => !open);
                setMenuError("");
              }}><Plus size={15}/> Add food item</button>
            </div>
            {(menuFeedback || menuError) && <div className={`admin-feedback ${menuError ? "error" : "success"}`}>{menuError || menuFeedback}</div>}
            {menuFormOpen && <form className="data-panel" onSubmit={saveMenuItem} style={{ marginBottom: 18 }}>
              <h3>{menuEditingId ? "Edit food item" : "Add new food item"}</h3>
              <div className="form-grid">
                <label>Food name<input required maxLength={120} value={menuForm.name} onChange={(e) => setMenuForm({ ...menuForm, name: e.target.value })} placeholder="e.g. Paneer Butter Masala"/></label>
                <label>Category<input value={menuForm.category} onChange={(e) => setMenuForm({ ...menuForm, category: e.target.value })} placeholder="Breakfast, Main Course, Snacks"/></label>
                <label>Price (₹)<input required type="number" min="0.01" step="0.01" value={menuForm.price} onChange={(e) => setMenuForm({ ...menuForm, price: e.target.value })} placeholder="199"/></label>
                <label>Food image URL<input type="url" value={menuForm.image_url} onChange={(e) => setMenuForm({ ...menuForm, image_url: e.target.value })} placeholder="https://example.com/food.jpg"/></label>
                <label className="form-full">Description<textarea rows="3" value={menuForm.description} onChange={(e) => setMenuForm({ ...menuForm, description: e.target.value })} placeholder="Describe the dish"/></label>
                <label className="form-check"><input type="checkbox" checked={menuForm.is_veg} onChange={(e) => setMenuForm({ ...menuForm, is_veg: e.target.checked })}/> Vegetarian</label>
                <label className="form-check"><input type="checkbox" checked={menuForm.is_available} onChange={(e) => setMenuForm({ ...menuForm, is_available: e.target.checked })}/> Available to customers</label>
              </div>
              <div className="panel-actions">
                <button className="admin-action" type="submit" disabled={menuSaving}>{menuSaving ? "Saving..." : menuEditingId ? "Save changes" : "Add food item"}</button>
                <button className="outline-button" type="button" disabled={menuSaving} onClick={() => { setMenuFormOpen(false); setMenuEditingId(null); setMenuForm(emptyMenuForm); }}>Cancel</button>
              </div>
            </form>}
            {menu.length ? <DataTable rows={menu} columns={[
              ["Item", (r) => <span>{r.name ?? r.item_name ?? "—"}{r.is_veg === true ? " · Veg" : r.is_veg === false ? " · Non-veg" : ""}</span>],
              ["Category", (r) => r.category ?? "—"],
              ["Price", (r) => money(r.price)],
              ["Availability", (r) => <StatusPill value={r.is_available === false ? "unavailable" : "available"} />],
              ["Actions", (r) => <div className="panel-actions"><button className="outline-button" disabled={menuSaving} onClick={() => editMenuItem(r)}>Edit</button><button className="outline-button" disabled={menuSaving} onClick={() => toggleMenuAvailability(r)}>{r.is_available === false ? "Make available" : "Mark unavailable"}</button><button className="admin-action danger" disabled={menuSaving} onClick={() => archiveMenuItem(r)}>Remove</button></div>]
            ]} /> : <EmptyState title="Your menu is empty" description="Add your first food item using the Add food item button." />}
          </section>
        ) : (
          <section className="data-panel"><div className="panel-heading"><h3>Latest orders</h3><button className="text-button" onClick={() => onNavigate("orders")}>View all <ChevronRight size={15} /></button></div>
            {orders.length ? <DataTable rows={(page === "orders" ? orders : orders.slice(0, 5))} columns={[
              ["Order", (r) => `#${r.order_id ?? r.id ?? "—"}`],
              ["Customer", (r) => r.customer_name ?? r.customer?.name ?? "Customer"],
              ["Status", (r) => <StatusPill value={r.status} />],
              ["Total", (r) => money(r.total_amount ?? r.total)]
            ]} /> : <EmptyState title="No orders received" description="New customer orders will appear here." />}
          </section>
        )}
      </>
    );
  }

  if (role === "delivery_partner") {
    const overview = data.overview || {};
    const requests = data.requests || [];
    const availability = overview.availability || "offline";
    const isOnline = availability === "online";
    const activeRequests = requests.filter((r) => !["delivered", "cancelled"].includes(r.status));
    const completedRequests = requests.filter((r) => r.status === "delivered");
    const nextStep = {
      assigned: { label: "Accept delivery", status: null },
      accepted: { label: "Reached restaurant", status: "arrived_restaurant" },
      arrived_restaurant: { label: "Picked up order", status: "picked_up" },
      picked_up: { label: "Start delivery", status: "on_the_way" },
      on_the_way: { label: "Mark delivered", status: "delivered" }
    };
    const statusLabel = (value) => ({
      assigned: "New assignment", accepted: "Accepted", arrived_restaurant: "At restaurant",
      picked_up: "Picked up", on_the_way: "On the way", delivered: "Delivered", cancelled: "Cancelled"
    }[value] || String(value || "Pending").replaceAll("_", " "));

    return (
      <div className="delivery-dashboard">
        <div className="dashboard-heading">
          <div><p className="eyebrow">DELIVERY OPERATIONS</p><h2>Your delivery workspace</h2><p className="delivery-subtitle">Manage assignments and keep customers and restaurants updated.</p></div>
          <button className="outline-button" onClick={onRefresh} disabled={deliveryBusy}><RefreshCw size={15} /> Refresh</button>
        </div>

        {(deliveryFeedback || deliveryError) && <div className={`admin-feedback ${deliveryError ? "error" : "success"}`}>{deliveryError || deliveryFeedback}</div>}

        <section className="delivery-availability-panel">
          <div className="delivery-availability-copy">
            <span className={`delivery-online-dot ${isOnline ? "online" : "offline"}`} />
            <div><strong>{isOnline ? "You are online" : "You are offline"}</strong><small>{isOnline ? "You can receive new delivery assignments." : "Switch online when you are ready to receive assignments."}</small></div>
          </div>
          <button className={`admin-action ${isOnline ? "danger" : ""}`} disabled={deliveryBusy} onClick={() => runDeliveryAction(() => setDeliveryAvailability(isOnline ? "offline" : "online"), isOnline ? "You are now offline." : "You are now online and available for assignments.")}>{isOnline ? "Go offline" : "Go online"}</button>
        </section>

        <div className="stats-grid">
          <StatCard icon={Package} label="Total deliveries" value={overview.total_deliveries ?? requests.length} />
          <StatCard icon={Clock} label="Active deliveries" value={overview.active_deliveries ?? activeRequests.length} />
          <StatCard icon={CheckCircle2} label="Completed deliveries" value={overview.completed_deliveries ?? completedRequests.length} />
          <StatCard icon={Bike} label="Availability" value={isOnline ? "Online" : "Offline"} />
        </div>

        <section className="data-panel delivery-requests-panel">
          <div className="panel-heading"><h3><ClipboardList size={18}/> My delivery assignments</h3><span>{requests.length} total</span></div>
          {requests.length ? <div className="delivery-request-list">
            {requests.map((request) => {
              const step = nextStep[request.status];
              const isActive = !["delivered", "cancelled"].includes(request.status);
              return <article className="delivery-request-card" key={request.delivery_id}>
                <div className="delivery-request-top"><div><span className="eyebrow">DELIVERY #{request.delivery_id}</span><h4>Order #{request.order_id}</h4></div><StatusPill value={request.status}/></div>
                <div className="delivery-request-meta"><span><Package size={14}/> {statusLabel(request.status)}</span><span><MapPin size={14}/> {request.current_location || "Location not shared yet"}</span></div>
                {isActive && step && <div className="delivery-progress-action">
                  <p>{request.status === "assigned" ? "A new order has been assigned to you." : "Update the delivery when you complete this step."}</p>
                  <button className="admin-action" disabled={deliveryBusy || (request.status === "assigned" && !isOnline)} onClick={() => runDeliveryAction(() => step.status ? updateDeliveryStatus(request.delivery_id, step.status) : acceptDelivery(request.delivery_id), step.status === "delivered" ? `Order #${request.order_id} marked delivered.` : `${step.label} completed for order #${request.order_id}.`)}>{step.label} <ArrowRight size={13}/></button>
                  {request.status === "assigned" && !isOnline && <small className="delivery-inline-hint">Go online before accepting a new assignment.</small>}
                </div>}
                {request.status === "delivered" && <p className="delivery-complete-note"><CheckCircle2 size={14}/> Delivery completed successfully.</p>}
                {request.status === "cancelled" && <p className="delivery-inline-hint">This assignment was cancelled.</p>}
                {isActive && <form className="delivery-location-form" onSubmit={(event) => { event.preventDefault(); if (!locationDraft.trim()) return; runDeliveryAction(() => updateDeliveryLocation(request.delivery_id, locationDraft.trim()), "Your latest location was shared with ShiftBite."); setLocationDraft(""); }}>
                  <input aria-label="Current delivery location" value={locationDraft} onChange={(event) => setLocationDraft(event.target.value)} placeholder="Enter current location (e.g. MG Road, Bengaluru)"/>
                  <button className="outline-button" type="submit" disabled={deliveryBusy || !locationDraft.trim()}><MapPin size={13}/> Share location</button>
                </form>}
              </article>;
            })}
          </div> : <EmptyState title="No delivery assignments yet" description={isOnline ? "You are online. New assignments from the admin will appear here." : "Go online to become available for assignments from the admin."}/>}
        </section>
        <p className="delivery-system-note"><ShieldCheck size={14}/> Delivery progress updates are saved to ShiftBite. Customers can follow order status, and the restaurant receives delivery progress notifications.</p>
      </div>
    );
  }

  const overview = data.overview || {};
  const users = data.users || [];
  const adminRestaurants = data.restaurants || [];
  return (
    <>
      <div className="dashboard-heading">
        <div><p className="eyebrow">PLATFORM CONTROL</p><h2>{({dashboard:"Administration overview", users:"User management", "restaurants-admin":"Restaurant approvals", "orders-admin":"Order monitoring", "delivery-admin":"Delivery operations", "support-admin":"Support centre"})[page] || "Administration overview"}</h2></div>
        <button className="outline-button" onClick={onRefresh}><RefreshCw size={15}/> Refresh</button>
      </div>
      <div className="stats-grid">
        <StatCard icon={Users} label="Total users" value={overview.total_users ?? users.length}/>
        <StatCard icon={Store} label="Restaurants" value={overview.total_restaurants ?? adminRestaurants.length}/>
        <StatCard icon={Clock} label="Pending restaurants" value={overview.pending_restaurants ?? "—"}/>
        <StatCard icon={ShoppingBag} label="Total orders" value={overview.total_orders ?? data.orders?.length ?? "—"}/>
        <StatCard icon={TrendingUp} label="Revenue" value={money(overview.total_revenue)}/>
      </div>
      {page === "dashboard" ? <>
        <div className="admin-quick-grid">
          {[["users", "Manage users", Users, users.length], ["restaurants-admin", "Review restaurants", Store, overview.pending_restaurants ?? 0], ["orders-admin", "Monitor orders", ClipboardList, data.orders?.length ?? 0], ["delivery-admin", "Delivery partners", Bike, data.deliveryPartners?.length ?? 0], ["support-admin", "Support tickets", Headset, data.tickets?.length ?? 0]].map(([target, label, Icon, count]) => <button className="admin-quick-card" key={target} onClick={() => onNavigate(target)}><span><Icon size={19}/></span><strong>{label}</strong><small>{count} records <ArrowRight size={13}/></small></button>)}
        </div>
        <section className="data-panel"><div className="panel-heading"><h3>Recent orders</h3><button className="text-button" onClick={() => onNavigate("orders-admin")}>View all <ChevronRight size={15}/></button></div>
          {data.orders?.length ? <DataTable rows={data.orders.slice(0,5)} columns={[["Order",(r)=>`#${r.order_id}`],["Customer ID",(r)=>r.user_id ?? "—"],["Status",(r)=><StatusPill value={r.status}/>],["Total",(r)=>money(r.total_amount)]]}/> : <EmptyState title="No orders yet" description="Orders will appear when customers place them."/>}
        </section>
      </> : <AdminControlCenter data={data} page={page} onRefresh={onRefresh}/>}
    </>
  );
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString("en-IN");
}

function StatusPill({ value }) {
  const label = String(value || "unknown").replaceAll("_", " ");
  return <span className={`status-pill status-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</span>;
}

function DataTable({ rows, columns }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr>{columns.map(([label]) => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id ?? row.order_id ?? row.user_id ?? row.restaurant_id ?? index}>
              {columns.map(([label, render]) => <td key={label}>{render(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("home");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [modal, setModal] = useState("");
  const [selectedRole, setSelectedRole] = useState("customer");
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("sb_user"));
    } catch {
      return null;
    }
  });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [restaurants, setRestaurants] = useState([]);
  const [search, setSearch] = useState("");
  const [backendStatus, setBackendStatus] = useState("checking");

  const [dashboardData, setDashboardData] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const roleInfo = roles.find((role) => role.id === session?.role);
  const RoleIcon = roleInfo?.icon || CircleUserRound;

  const filteredRestaurants = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return restaurants;
    return restaurants.filter((restaurant) =>
      [restaurant.name, restaurant.cuisine, restaurant.address]
        .filter(Boolean).join(" ").toLowerCase().includes(term)
    );
  }, [restaurants, search]);

  useEffect(() => {
    checkBackend().then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
    loadRestaurants();
  }, []);

  useEffect(() => {
    if (session) loadDashboard();
  }, [session]);

  const loadRestaurants = async () => {
    try {
      const restaurantData = await getRestaurants();
      setRestaurants(getArray(restaurantData, ["restaurants", "items", "results"]));
    } catch {
      setRestaurants([]);
    }
  };

  const loadDashboard = async () => {
    if (!session?.role) return;
    setDashboardLoading(true);
    setDashboardError("");
    try {
      let result = {};
      switch (session.role) {
        case "customer": {
          const [orders, cart] = await Promise.all([getMyOrders(), api.get("/cart")]);
          result = { orders: getArray(orders, ["orders", "items"]), cart: cart.data };
          break;
        }
        case "restaurant_owner": {
          const [overview, orders, menu] = await Promise.all([
            getRestaurantDashboard(), getRestaurantOrders(), getRestaurantMenu()
          ]);
          result = {
            overview,
            orders: getArray(orders, ["orders", "items"]),
            menu: getArray(menu, ["items", "menu", "menu_items"])
          };
          break;
        }
        case "delivery_partner": {
          const [overview, requests] = await Promise.all([
            api.get("/delivery-partners/me/dashboard"), getDeliveryRequests()
          ]);
          result = {
            overview: overview.data,
            requests: getArray(requests, ["requests", "deliveries", "items"])
          };
          break;
        }
        case "admin": {
          const [overview, users, restaurantData, orders, deliveryPartners, tickets] = await Promise.all([
            getAdminDashboard(), getAdminUsers(), getAdminRestaurants(),
            api.get("/admin/orders"), api.get("/admin/delivery-partners"),
            api.get("/support/tickets")
          ]);
          result = {
            overview,
            users: getArray(users, ["users", "items"]),
            restaurants: getArray(restaurantData, ["restaurants", "items"]),
            orders: getArray(orders.data, ["orders", "items"]),
            deliveryPartners: getArray(deliveryPartners.data, ["delivery_partners", "partners", "items"]),
            tickets: getArray(tickets.data, ["tickets", "items"])
          };
          break;
        }
      }
      setDashboardData(result);
    } catch (err) {
      setDashboardError(err.response?.data?.detail ||
        "Some dashboard information could not be loaded. Please refresh.");
    } finally {
      setDashboardLoading(false);
    }
  };

  const openLogin = (role = "customer") => {
    setSelectedRole(role);
    setModal("login");
    setError("");
    setNotice("");
    setPassword("");
  };

  const closeModal = () => {
    setModal("");
    setError("");
    setNotice("");
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await loginUser({ email, password });
      if (!data.access_token || !data.role) {
        throw new Error("Login response is missing the token or role.");
      }
      if (data.role !== selectedRole) {
        throw new Error(`This account belongs to the ${data.role.replaceAll("_", " ")} portal. Please select the correct portal.`);
      }
      const user = {
        user_id: data.user_id,
        name: data.name || "ShiftBite User",
        email,
        role: data.role
      };
      localStorage.setItem("sb_token", data.access_token);
      localStorage.setItem("sb_user", JSON.stringify(user));
      setSession(user);
      setPage("dashboard");
      closeModal();
      setEmail("");
      setPassword("");
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (event) => {
  event.preventDefault();
  setLoading(true);
  setError("");
  setNotice("");

  try {
    if (selectedRole === "delivery_partner") {
      await registerDeliveryPartner({
        name,
        email,
        phone: phone || null,
        password,
      });

      setNotice(
        "Your delivery partner account has been created. You can now sign in."
      );

    } else if (selectedRole === "restaurant_owner") {
      await registerRestaurant({
        name,
        email,
        phone: phone || null,
        password,
        restaurant_name: restaurantName,
        address,
        cuisine,
      });

      setNotice(
        "Your restaurant registration has been submitted for approval."
      );

    } else if (selectedRole === "customer") {
      await registerCustomer({
        name,
        email,
        phone: phone || null,
        password,
      });

      setNotice(
        "Your customer account has been created. You can now sign in."
      );

    } else {
      throw new Error("Invalid registration portal selected.");
    }

    setModal("login");
    setPassword("");

  } catch (err) {
    setError(
      err.response?.data?.detail ||
      err.message ||
      "Registration failed. Please check your details."
    );
  } finally {
    setLoading(false);
  }
};

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch { /* local logout still proceeds */ }
    localStorage.removeItem("sb_token");
    localStorage.removeItem("sb_user");
    setSession(null);
    setDashboardData(null);
    setPage("home");
  };

  const scrollToRestaurants = () => {
    document.getElementById("restaurants")?.scrollIntoView({ behavior: "smooth" });
  };

  if (session) {
    return (
      <div className="lux-app dashboard-app">
        <aside className="side-nav">
          <Brand />
          <p className="side-label">WORKSPACE</p>
          <button className={`side-link ${page === "dashboard" ? "active" : ""}`} onClick={() => setPage("dashboard")}><LayoutDashboard size={18} /> Overview</button>
          {session.role === "customer" && <button className={`side-link ${page === "orders" ? "active" : ""}`} onClick={() => setPage("orders")}><Package size={18} /> My orders</button>}
          {session.role === "restaurant_owner" && <>
            <button className={`side-link ${page === "orders" ? "active" : ""}`} onClick={() => setPage("orders")}><ShoppingBag size={18} /> Orders</button>
            <button className={`side-link ${page === "menu" ? "active" : ""}`} onClick={() => setPage("menu")}><Utensils size={18} /> Menu management</button>
          </>}
          {session.role === "admin" && <>
            <button className={`side-link ${page === "users" ? "active" : ""}`} onClick={() => setPage("users")}><Users size={18}/> Users</button>
            <button className={`side-link ${page === "restaurants-admin" ? "active" : ""}`} onClick={() => setPage("restaurants-admin")}><Store size={18}/> Restaurants</button>
            <button className={`side-link ${page === "orders-admin" ? "active" : ""}`} onClick={() => setPage("orders-admin")}><ClipboardList size={18}/> Orders</button>
            <button className={`side-link ${page === "delivery-admin" ? "active" : ""}`} onClick={() => setPage("delivery-admin")}><Bike size={18}/> Delivery partners</button>
            <button className={`side-link ${page === "support-admin" ? "active" : ""}`} onClick={() => setPage("support-admin")}><Headset size={18}/> Support tickets</button>
          </>}
          <div className="side-bottom">
            <div className="profile-mini">
              <span className="avatar">{session.name?.charAt(0)?.toUpperCase() || "S"}</span>
              <span><strong>{session.name}</strong><small>{roleInfo?.label || session.role}</small></span>
            </div>
            <button className="side-link logout-link" onClick={logout}><LogOut size={18} /> Sign out</button>
          </div>
        </aside>
        <main className="workspace">
          <header className="workspace-topbar">
            <div><p className="eyebrow">SHIFTBITE / WORKSPACE</p><h2>{roleInfo?.label || "Dashboard"} portal</h2></div>
            <button className="icon-button" onClick={loadDashboard} aria-label="Refresh dashboard"><RefreshCw size={18} /></button>
          </header>
          <section className="workspace-content">
            <div className="welcome-banner">
              <div><p className="eyebrow">YOUR SHIFTBITE EXPERIENCE</p><h1>Welcome back, {session.name?.split(" ")[0]}.</h1><p>Your workspace is ready. Here's your latest overview.</p></div>
              <div className="welcome-emblem"><RoleIcon size={43} /></div>
            </div>
            {dashboardLoading && <div className="state-panel"><RefreshCw className="spin" /> Loading your dashboard...</div>}
            {dashboardError && <div className="error-panel">{dashboardError}<button className="text-button" onClick={loadDashboard}>Try again</button></div>}
            {!dashboardLoading && dashboardData && <DashboardContent role={session.role} data={dashboardData} page={page} onNavigate={setPage} onRefresh={loadDashboard} restaurants={restaurants} onCartUpdated={loadDashboard} />}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="lux-app">
      <nav className="lux-navbar">
        <Brand />
        <div className={`lux-nav-links ${mobileMenu ? "nav-open" : ""}`}>
          <a href="#home" onClick={() => setMobileMenu(false)}>Home</a>
          <a href="#restaurants" onClick={() => setMobileMenu(false)}>Discover</a>
          <a href="#experience" onClick={() => setMobileMenu(false)}>Our experience</a>
          <a href="#portals" onClick={() => setMobileMenu(false)}>Portals</a>
          <button className="gold-button nav-cta" onClick={() => openLogin()}>Sign in <ArrowRight size={16} /></button>
        </div>
        <button className="mobile-menu-btn" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Toggle navigation">{mobileMenu ? <X /> : <Menu />}</button>
      </nav>

      <main>
        <section className="lux-hero" id="home">
          <div className="hero-copy">
            <div className="lux-kicker"><Sparkles size={14} /> THE ART OF GOOD FOOD</div>
            <h1>Exceptional taste.<br /><span>Effortlessly delivered.</span></h1>
            <p>Discover remarkable restaurants and thoughtfully prepared favourites. A more considered way to enjoy every meal.</p>
            <div className="hero-buttons">
              <button className="gold-button" onClick={scrollToRestaurants}>Explore restaurants <ArrowRight size={17} /></button>
              <button className="outline-button" onClick={() => openLogin("customer")}>Join ShiftBite</button>
            </div>
            <div className="hero-trust">
              <span><Star size={15} /> Curated experiences</span>
              <span><Clock size={15} /> Convenient ordering</span>
              <span><MapPin size={15} /> Order updates</span>
            </div>
          </div>
          <div className="hero-art">
            <div className="hero-image-frame">
              <img src="https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1100&q=85" alt="Beautifully presented gourmet meal" />
              <div className="image-caption"><span>THE SHIFTBITE EDIT</span><strong>A taste worth slowing down for.</strong></div>
            </div>
            <div className="hero-stamp"><Utensils size={21} /><span>GOOD FOOD<br />GREAT MOOD</span></div>
          </div>
        </section>

        <section className="lux-intro" id="experience">
          <p className="eyebrow">A BETTER WAY TO DINE</p>
          <h2>Made for moments<br />that <span>matter.</span></h2>
          <p>From discovering a new favourite to following every order, ShiftBite brings the dining journey together in one place.</p>
        </section>

        <section className="restaurant-section" id="restaurants">
          <div className="section-topline">
            <div><p className="eyebrow">DISCOVER SOMETHING DELICIOUS</p><h2>Restaurants worth <span>discovering.</span></h2></div>
            <div className="restaurant-search"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search restaurants or cuisine" /></div>
          </div>
          {filteredRestaurants.length > 0 ? (
            <div className="restaurant-grid">
              {filteredRestaurants.map((restaurant, index) => (
                <article className="restaurant-card" key={restaurant.restaurant_id || index}>
                  <div className="restaurant-photo">
                    <img src={restaurant.image_url || [
                      "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80",
                      "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=900&q=80",
                      "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=900&q=80"
                    ][index % 3]} alt={restaurant.name || "Restaurant"} />
                    <span className="photo-tag">{restaurant.cuisine || "CURATED DINING"}</span>
                  </div>
                  <div className="restaurant-info">
                    <h3>{restaurant.name || "Restaurant"}</h3>
                    <p>{restaurant.address || restaurant.description || "Discover the menu and explore the experience."}</p>
                    <div className="restaurant-meta"><span><Star size={14} /> {restaurant.rating || "New"}</span><span><Clock size={14} /> {restaurant.delivery_time || "Delivery available"}</span></div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-restaurants"><Store size={30} /><h3>No restaurants to display yet</h3><p>Approved and open restaurants will appear here when available.</p><button className="outline-button" onClick={loadRestaurants}>Refresh restaurants <RefreshCw size={15} /></button></div>
          )}
        </section>

        <section className="portal-section" id="portals">
          <div className="lux-intro"><p className="eyebrow">ONE CONNECTED PLATFORM</p><h2>Every role. One <span>experience.</span></h2><p>Choose your workspace to access your ShiftBite portal.</p></div>
          <div className="lux-portal-grid">
            {roles.map((role) => {
              const Icon = role.icon;
              return <button className="lux-portal-card" key={role.id} onClick={() => openLogin(role.id)}>
                <span className="portal-card-icon"><Icon size={23} /></span>
                <span><strong>{role.label}</strong><small>Access your workspace</small></span>
                <ArrowRight size={18} />
              </button>;
            })}
          </div>
        </section>
      </main>

      <footer className="lux-footer"><Brand /><p>Exceptional taste. Effortlessly delivered.</p><span>© {new Date().getFullYear()} ShiftBite. All rights reserved.</span></footer>

      {backendStatus === "offline" && <div className="backend-alert">Backend connection unavailable. Please check that FastAPI is running.</div>}

      {modal && (
        <div className="lux-modal-backdrop" onMouseDown={closeModal}>
          <section className="lux-modal" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-x" onClick={closeModal} aria-label="Close"><X size={20} /></button>
            <div className="modal-brand"><Utensils size={23} /></div>
            <p className="eyebrow">WELCOME TO SHIFTBITE</p>
            <h2>{modal === "register" ? "Create your account." : "Welcome back."}</h2>
            <p className="modal-description">{modal === "register" ? "Begin your ShiftBite experience." : "Sign in to continue to your personal workspace."}</p>

            <div className="role-select">
              {roles.map((role) => {
                const Icon = role.icon;
                return <button type="button" key={role.id} className={selectedRole === role.id ? "role-choice selected" : "role-choice"} onClick={() => { setSelectedRole(role.id); setError(""); }}>
                  <Icon size={16} /><span>{role.label}</span>
                </button>;
              })}
            </div>

            <form onSubmit={modal === "register" ? handleRegister : handleLogin}>
              {modal === "register" && <>
                <label htmlFor="full-name">Full name</label>
                <input id="full-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Enter your full name" required />
                <label htmlFor="phone">Phone number</label>
                <input id="phone" type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="Enter your phone number" />
              </>}
              <label htmlFor="email">Email address</label>
              <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required />
              <label htmlFor="password">Password</label>
              <div className="password-field">
                <input id="password" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" autoComplete={modal === "register" ? "new-password" : "current-password"} required />
                <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button>
              </div>

              {error && <p className="form-error">{error}</p>}
              {notice && <p className="form-notice">{notice}</p>}
              <button className="gold-button form-submit" type="submit" disabled={loading}>
                {loading ? "Please wait..." : modal === "register" ? "Create account" : "Sign in"}
                {!loading && <ArrowRight size={17} />}
              </button>
            </form>

            <p className="modal-switch">
              {modal === "register" ? "Already have an account?" : "New to ShiftBite?"}
              <button type="button" onClick={() => { setModal(modal === "register" ? "login" : "register"); setError(""); setNotice(""); }}>
                {modal === "register" ? "Sign in" : "Create account"}
              </button>
            </p>
            {selectedRole !== "customer" && modal === "register" && <p className="form-hint">This form creates customer accounts only. Restaurant and delivery partner registration use their dedicated registration endpoints.</p>}
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
