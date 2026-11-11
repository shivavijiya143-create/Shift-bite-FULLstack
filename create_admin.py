from getpass import getpass

from Backend.database import SessionLocal
from Backend import models as m
from Backend.security import hash_password

db = SessionLocal()

try:
    print("\n=== SHIFTBITE ADMIN CREATION ===")

    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Create admin password: ")
    confirm = getpass("Confirm password: ")

    if not name or not email or not password:
        raise ValueError("All fields are required.")

    if password != confirm:
        raise ValueError("Passwords do not match.")

    if db.query(m.User).filter(m.User.email == email).first():
        raise ValueError("This email already exists. Use another email.")

    admin = m.User(
        name=name,
        email=email,
        phone=None,
        password_hash=hash_password(password),
        role="admin",
        status="active"
    )

    db.add(admin)
    db.commit()

    print("\nAdmin account created successfully!")
    print("Email:", email)
    print("Role: admin")
    print("Status: active")

except Exception as error:
    db.rollback()
    print("\nError:", error)

finally:
    db.close()