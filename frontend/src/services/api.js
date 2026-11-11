import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Automatically attach the authenticated user's JWT.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sb_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Handle expired or invalid sessions.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("sb_token");
      localStorage.removeItem("sb_user");
    }

    return Promise.reject(error);
  }
);

// Authentication
export const loginUser = async (credentials) => {
  const { data } = await api.post("/auth/login", credentials);
  return data;
};

export const registerCustomer = async (details) => {
  const { data } = await api.post("/auth/register", details);
  return data;
};

export const registerRestaurant = async (details) => {
  const { data } = await api.post("/auth/register/restaurant", details);
  return data;
};

export const registerDeliveryPartner = async (details) => {
  const { data } = await api.post("/auth/register/delivery", details);
  return data;
};

export const logoutUser = async () => {
  try {
    await api.post("/auth/logout");
  } finally {
    localStorage.removeItem("sb_token");
    localStorage.removeItem("sb_user");
  }
};

export const getCurrentUser = async () => {
  const { data } = await api.get("/auth/me");
  return data;
};

// Customer discovery
export const getHome = async () => {
  const { data } = await api.get("/home");
  return data;
};

export const getRestaurants = async (params = {}) => {
  const { data } = await api.get("/restaurants", { params });
  return data;
};

export const searchRestaurants = async (params = {}) => {
  const { data } = await api.get("/search", { params });
  return data;
};

// Customer cart and checkout
export const getCart = async () => {
  const { data } = await api.get("/cart");
  return data;
};

export const addCartItem = async (details) => {
  const { data } = await api.post("/cart/items", details);
  return data;
};

export const updateCartItem = async (id, details) => {
  const { data } = await api.patch(`/cart/items/${id}`, details);
  return data;
};

export const removeCartItem = async (id) => {
  const { data } = await api.delete(`/cart/items/${id}`);
  return data;
};

export const validateCheckout = async (details) => {
  const { data } = await api.post("/checkout/validate", details);
  return data;
};

export const placeOrder = async (details) => {
  const { data } = await api.post("/orders", details);
  return data;
};

export const getMyOrders = async () => {
  const { data } = await api.get("/orders");
  return data;
};

// Restaurant portal
export const getRestaurantDashboard = async () => {
  const { data } = await api.get("/restaurant-portal/dashboard/stats");
  return data;
};

export const getRestaurantOrders = async () => {
  const { data } = await api.get("/restaurant-portal/orders");
  return data;
};

export const getRestaurantMenu = async () => {
  const { data } = await api.get("/restaurant-portal/menu");
  return data;
};

// Delivery portal
export const getDeliveryRequests = async () => {
  const { data } = await api.get("/delivery-partners/me/requests");
  return data;
};

export const setDeliveryAvailability = async (availability) => {
  const { data } = await api.patch(
    "/delivery-partners/me/availability",
    { availability }
  );
  return data;
};

export const acceptDelivery = async (deliveryId) => {
  const { data } = await api.post(`/deliveries/${deliveryId}/accept`);
  return data;
};

export const updateDeliveryStatus = async (deliveryId, status) => {
  const { data } = await api.patch(`/deliveries/${deliveryId}/status`, { status });
  return data;
};

export const updateDeliveryLocation = async (deliveryId, location) => {
  const { data } = await api.patch(`/deliveries/${deliveryId}/location`, { location });
  return data;
};

// Admin portal
export const getAdminDashboard = async () => {
  const { data } = await api.get("/admin/dashboard/stats");
  return data;
};

export const getAdminUsers = async (params = {}) => {
  const { data } = await api.get("/admin/users", { params });
  return data;
};

export const getAdminRestaurants = async (params = {}) => {
  const { data } = await api.get("/admin/restaurants", { params });
  return data;
};

// Admin operations (all routes verified against Backend/main.py)
export const updateAdminUserStatus = async (userId, status) => {
  const { data } = await api.patch(`/admin/users/${userId}/status`, { status });
  return data;
};

export const approveRestaurant = async (restaurantId) => {
  const { data } = await api.post(`/admin/restaurants/${restaurantId}/approve`);
  return data;
};

export const rejectRestaurant = async (restaurantId) => {
  const { data } = await api.post(`/admin/restaurants/${restaurantId}/reject`);
  return data;
};

export const getAdminOrders = async (params = {}) => {
  const { data } = await api.get("/admin/orders", { params });
  return data;
};

export const getAdminDeliveryPartners = async () => {
  const { data } = await api.get("/admin/delivery-partners");
  return data;
};

export const assignDeliveryPartner = async (orderId, partnerId) => {
  const { data } = await api.post(`/admin/orders/${orderId}/assign`, { partner_id: partnerId });
  return data;
};

export const getSupportTickets = async () => {
  const { data } = await api.get("/support/tickets");
  return data;
};

export const updateSupportTicket = async (ticketId, details) => {
  const { data } = await api.patch(`/admin/support/tickets/${ticketId}`, details);
  return data;
};

// Backend status
export const checkBackend = async () => {
  const { data } = await api.get("/health");
  return data;
};

export default api;
