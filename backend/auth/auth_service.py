import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.config import settings
from backend.database import get_db
from backend.models import User, Supplier, Buyer, Financier, Invoice, Offer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + '$' + key.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if '$' not in hashed_password:
            return False
        salt_hex, key_hex = hashed_password.split('$')
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return new_key == key
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        if user_id is None or email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_role(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to access this resource"
            )
        return current_user
    return role_checker

def verify_invoice_access(invoice: Invoice, user: User, db: Session):
    """Enforces Object-Level Access Control (IDOR Prevention) on Invoice entities.
    - Supplier can ONLY access invoices where Invoice.supplier_id == current_user.supplier_profile.id.
    - Buyer can ONLY access invoices where Invoice.buyer_id == current_user.buyer_profile.id.
    - Financier can access verified invoices eligible for funding.
    - Admin can access all invoices.
    """
    if user.role == "admin":
        return True

    if user.role == "supplier":
        supplier = db.query(Supplier).filter(Supplier.user_id == user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this invoice resource")
        return True

    if user.role == "buyer":
        buyer = db.query(Buyer).filter(Buyer.user_id == user.id).first()
        if not buyer or invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: This invoice is not assigned to your buyer profile")
        return True

    if user.role == "financier":
        if invoice.status not in ["VERIFIED", "OFFER_EXTENDED", "FINANCED", "SETTLED"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Unverified invoice is not accessible to financiers")
        return True

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role access to invoice resource")

def verify_offer_access(offer: Offer, user: User, db: Session):
    """Enforces Object-Level Access Control (IDOR Prevention) on Offer entities."""
    if user.role == "admin":
        return True

    if user.role == "supplier":
        supplier = db.query(Supplier).filter(Supplier.user_id == user.id).first()
        if not supplier or offer.invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Offer is for an invoice you do not own")
        return True

    if user.role == "financier":
        financier = db.query(Financier).filter(Financier.user_id == user.id).first()
        if not financier or offer.financier_id != financier.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You did not submit this offer")
        return True

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to offer resource")
