from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Supplier, Buyer, Financier
from backend.schemas import UserCreate, UserResponse, UserLogin, Token
from backend.auth.auth_service import hash_password, verify_password, create_access_token, get_current_user
from backend.security.rate_limiter import auth_rate_limiter
from backend.security.audit_logger import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    auth_rate_limiter.check_rate_limit(request)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Admin accounts cannot be freely self-registered
    if user_in.role.lower() == "admin":
        log_audit_event(db, action="ADMIN_REGISTER_ATTEMPT_BLOCKED", ip_address=client_ip, details={"email": user_in.email})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration of admin role is strictly forbidden"
        )
    
    if user_in.role.lower() not in ["supplier", "buyer", "financier"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: supplier, buyer, financier"
        )

    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    new_user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role.lower()
    )
    db.add(new_user)
    db.flush()

    # Create role profile
    if new_user.role == "supplier":
        company_name = user_in.company_name or user_in.full_name
        tax_id = user_in.tax_id or f"TAX-SUP-{new_user.id[:8].upper()}"
        supplier = Supplier(
            user_id=new_user.id,
            company_name=company_name,
            tax_id=tax_id
        )
        db.add(supplier)
    elif new_user.role == "buyer":
        company_name = user_in.company_name or user_in.full_name
        tax_id = user_in.tax_id or f"TAX-BUY-{new_user.id[:8].upper()}"
        buyer = Buyer(
            user_id=new_user.id,
            company_name=company_name,
            tax_id=tax_id
        )
        db.add(buyer)
    elif new_user.role == "financier":
        institution_name = user_in.institution_name or user_in.full_name
        financier = Financier(
            user_id=new_user.id,
            institution_name=institution_name,
            liquidity_pool=user_in.liquidity_pool or 5000000.0,
            min_acceptable_apr=user_in.min_acceptable_apr or 5.0,
            max_risk_tolerance=user_in.max_risk_tolerance or 40.0
        )
        db.add(financier)

    db.commit()
    db.refresh(new_user)

    log_audit_event(
        db,
        action="USER_REGISTERED",
        user_id=new_user.id,
        resource_type="User",
        resource_id=new_user.id,
        ip_address=client_ip,
        details={"email": new_user.email, "role": new_user.role}
    )

    return new_user

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    auth_rate_limiter.check_rate_limit(request)
    client_ip = request.client.host if request.client else "127.0.0.1"

    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password) or not user.is_active:
        log_audit_event(
            db,
            action="LOGIN_FAILED",
            user_id=user.id if user else None,
            ip_address=client_ip,
            details={"email": user_credentials.email}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(data={"user_id": user.id, "email": user.email, "role": user.role})
    
    # Optionally set HttpOnly cookie for browser authorization safety
    response.set_cookie(
        key="scf_access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=False # Set to True in HTTPS production
    )

    log_audit_event(
        db,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        resource_type="User",
        resource_id=user.id,
        ip_address=client_ip,
        details={"role": user.role}
    )

    return Token(access_token=token, token_type="bearer", user=user)

@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie(key="scf_access_token")
    log_audit_event(db, action="USER_LOGOUT", user_id=current_user.id, resource_type="User", resource_id=current_user.id)
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
