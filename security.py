import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from .database import get_db
from .models import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-this-secret")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "120"))
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def hash_password(password): return pwd.hash(password)
def verify_password(password, hashed): return pwd.verify(password, hashed)
def create_token(user):
    payload = {"sub": str(user.user_id), "role": user.role,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    error = HTTPException(status_code=401, detail="Invalid or expired token",
                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise error
    user = db.query(User).filter(User.user_id == user_id, User.status == "active").first()
    if not user: raise error
    return user

def allow(*roles):
    def checker(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You are not allowed to perform this action")
        return user
    return checker
