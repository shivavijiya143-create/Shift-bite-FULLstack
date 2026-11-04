# ShiftBite — Food Delivery Application

Stack: React + Vite, Python FastAPI, MySQL.

## Included modules
1. User registration & authentication
2. Location & address management
3. Restaurant discovery & search
4. Menu & item management
5. Cart & customization
6. Checkout, offers & pricing
7. Payment management (COD/demo status; gateway adapter placeholder)
8. Order management
9. Delivery partner & dispatch
10. Live tracking & notifications (database-backed demo; GPS/provider integration placeholder)
11. Ratings, reviews & support
12. Restaurant partner portal
13. Admin console & analytics

## Backend setup
1. Install MySQL and create a database:
   `CREATE DATABASE shiftbite CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. Open `backend/`, create `.env` from `.env.example`, and set your MySQL username/password and a long random `SECRET_KEY`.
3. Create a virtual environment and install dependencies:
   `python -m venv .venv`
   Windows: `.venv\\Scripts\\activate`
   macOS/Linux: `source .venv/bin/activate`
   `pip install -r requirements.txt`
4. Start API:
   `uvicorn app.main:app --reload`
5. API docs: http://127.0.0.1:8000/docs

The backend creates tables on first start for a college/demo environment. For production, use Alembic migrations, HTTPS, proper secrets management, backups and security review.

## Frontend setup
1. Open `frontend/`
2. `npm install`
3. `npm run dev`
4. Open the Vite URL shown in the terminal.

Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env` if needed.

## Demo roles
Register through `/api/v1/auth/register`. Public registration only permits `customer`.
Create restaurant_owner, delivery_partner and admin accounts through a controlled database/admin process; never expose role elevation in public registration.

## Important integration notes
- Online payment gateway, OTP/email/SMS/push, maps and real-time GPS require provider credentials and configuration. This project records demo payment states and tracking updates but does not pretend to complete external transactions.
- Checkout fees and promotion rules are simple configurable demo defaults in `app/services.py`; confirm final rules with your project guide.
- Dispatch is manual through admin/restaurant assignment endpoints.
- Do not store raw card details. Payment provider references only.
