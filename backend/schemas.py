from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, ConfigDict

# --- Auth Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str # supplier, buyer, financier, admin

class UserCreate(UserBase):
    password: str
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    institution_name: Optional[str] = None
    liquidity_pool: Optional[float] = 5000000.0
    min_acceptable_apr: Optional[float] = 5.0
    max_risk_tolerance: Optional[float] = 40.0


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str

# --- Entity Profiles ---
class SupplierCreate(BaseModel):
    company_name: str
    tax_id: str

class SupplierResponse(BaseModel):
    id: str
    user_id: str
    company_name: str
    tax_id: str
    credit_rating: str
    risk_score: float
    total_funded_amount: float

    model_config = ConfigDict(from_attributes=True)

class BuyerCreate(BaseModel):
    company_name: str
    tax_id: str
    max_credit_limit: float = 1000000.0

class BuyerResponse(BaseModel):
    id: str
    user_id: str
    company_name: str
    tax_id: str
    credit_rating: str
    max_credit_limit: float
    used_credit_limit: float

    model_config = ConfigDict(from_attributes=True)

class FinancierCreate(BaseModel):
    institution_name: str
    liquidity_pool: float = 5000000.0
    min_acceptable_apr: float = 5.0
    max_risk_tolerance: float = 40.0

class FinancierResponse(BaseModel):
    id: str
    user_id: str
    institution_name: str
    liquidity_pool: float
    min_acceptable_apr: float
    max_risk_tolerance: float

    model_config = ConfigDict(from_attributes=True)

# --- Invoice Schemas ---
class InvoiceCreate(BaseModel):
    invoice_number: str
    buyer_id: str
    amount: float
    currency: str = "USD"
    issue_date: date
    due_date: date
    description: Optional[str] = None

class InvoiceStatusUpdate(BaseModel):
    status: str

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    supplier_id: str
    buyer_id: str
    amount: float
    currency: str
    issue_date: date
    due_date: date
    status: str
    description: Optional[str]
    document_hash: Optional[str]
    created_at: datetime
    supplier_company_name: Optional[str] = None
    buyer_company_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# --- Verification Schemas ---
class VerificationCreate(BaseModel):
    invoice_id: str
    is_valid: bool
    buyer_comments: Optional[str] = None

class VerificationResponse(BaseModel):
    id: str
    invoice_id: str
    buyer_id: str
    verified_by_user_id: str
    is_valid: bool
    verification_hash: str
    buyer_comments: Optional[str]
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Risk Engine Schemas ---
class RiskAssessmentRequest(BaseModel):
    supplier_id: str
    buyer_id: str
    invoice_amount: float
    tenor_days: int

class RiskAssessmentResponse(BaseModel):
    risk_score: float # 0 - 100
    risk_level: str   # LOW, MEDIUM, HIGH
    credit_decision: str
    supplier_credit_rating: str
    buyer_credit_rating: str
    recommended_max_advance_pct: float
    recommended_base_apr_pct: float
    ai_risk_analysis: str
    demo_notice: Optional[str] = None

# --- Match & Suitability Schemas ---
class MatchRecommendationResponse(BaseModel):
    invoice_id: str
    financier_id: str
    financier_name: str
    match_score: float
    suitability_score: float
    is_eligible: bool
    calculated_risk_score: float
    recommended_apr: float
    ai_match_rationale: str
    explainability_reasons: List[str]

# --- Offer Schemas ---
class OfferCreate(BaseModel):
    invoice_id: str
    discount_rate_pct: float
    apr_pct: float
    tenor_days: int
    custom_offered_amount: Optional[float] = None
    expires_in_hours: int = 72

class OfferResponse(BaseModel):
    id: str
    invoice_id: str
    financier_id: str
    requested_amount: float
    offered_amount: float
    discount_rate_pct: float
    apr_pct: float
    tenor_days: int
    status: str
    expires_at: datetime
    created_at: datetime
    financier_name: Optional[str] = None
    suitability_score: Optional[float] = None
    explainability_reasons: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

# --- Financing & Transaction Schemas ---
class DisbursementRequest(BaseModel):
    offer_id: str
    recipient_account: str

class TransactionResponse(BaseModel):
    id: str
    invoice_id: str
    offer_id: str
    transaction_type: str
    amount: float
    sender_account: str
    recipient_account: str
    transaction_hash: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Settlement Schemas ---
class SettlementCreate(BaseModel):
    invoice_id: str
    payment_amount: float
    payer_account: str

class SettlementResponse(BaseModel):
    invoice_id: str
    total_paid: float
    financier_payout: float
    supplier_rebate: float
    disbursement_hash: str
    status: str
    settled_at: datetime

# --- Notification Schemas ---
class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    category: str

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    category: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- System Overview Statistics ---
class SystemStatsResponse(BaseModel):
    total_users: int
    total_suppliers: int
    total_buyers: int
    total_financiers: int
    total_invoices_count: int
    total_invoices_volume: float
    total_funded_volume: float
    total_settled_volume: float
    active_liquidity_pool: float
