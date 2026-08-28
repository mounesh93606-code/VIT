import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.connection.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # supplier, buyer, financier, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier_profile = relationship("Supplier", back_populates="user", uselist=False, cascade="all, delete-orphan")
    buyer_profile = relationship("Buyer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    financier_profile = relationship("Financier", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    tax_id = Column(String(100), unique=True, nullable=False)
    credit_rating = Column(String(10), default="BBB")
    risk_score = Column(Float, default=25.0)  # 0-100 scale (lower is lower risk)
    total_funded_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="supplier_profile")
    invoices = relationship("Invoice", back_populates="supplier")


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name = Column(String(255), nullable=False)
    tax_id = Column(String(100), unique=True, nullable=False)
    credit_rating = Column(String(10), default="AA")
    max_credit_limit = Column(Float, default=1000000.0)
    used_credit_limit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="buyer_profile")
    invoices = relationship("Invoice", back_populates="buyer")
    verifications = relationship("Verification", back_populates="buyer")


class Financier(Base):
    __tablename__ = "financiers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_name = Column(String(255), nullable=False)
    liquidity_pool = Column(Float, default=5000000.0)
    min_acceptable_apr = Column(Float, default=5.0)
    max_risk_tolerance = Column(Float, default=40.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="financier_profile")
    offers = relationship("Offer", back_populates="financier")
    match_recommendations = relationship("MatchRecommendation", back_populates="financier")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    buyer_id = Column(String(36), ForeignKey("buyers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(50), default="PENDING_VERIFICATION")
    # PENDING_VERIFICATION -> VERIFIED -> OFFER_EXTENDED -> FINANCED -> SETTLED / REJECTED
    description = Column(Text, nullable=True)
    document_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="invoices")
    buyer = relationship("Buyer", back_populates="invoices")
    verification = relationship("Verification", back_populates="invoice", uselist=False)
    risk_assessments = relationship("RiskAssessment", back_populates="invoice", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="invoice")
    match_recommendations = relationship("MatchRecommendation", back_populates="invoice", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="invoice")


class Verification(Base):
    __tablename__ = "verification"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), unique=True, nullable=False)
    buyer_id = Column(String(36), ForeignKey("buyers.id"), nullable=False)
    verified_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_valid = Column(Boolean, nullable=False)
    verification_hash = Column(String(255), nullable=False)
    buyer_comments = Column(Text, nullable=True)
    verified_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="verification")
    buyer = relationship("Buyer", back_populates="verifications")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    composite_risk_score = Column(Float, nullable=False) # 0-100 scale
    risk_level = Column(String(50), nullable=False) # LOW, MEDIUM, HIGH
    credit_decision = Column(String(50), nullable=False) # APPROVE, MANUAL_REVIEW, REJECT
    recommended_base_apr_pct = Column(Float, nullable=False)
    eval_factors_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="risk_assessments")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    financier_id = Column(String(36), ForeignKey("financiers.id"), nullable=False)
    requested_amount = Column(Float, nullable=False)
    offered_amount = Column(Float, nullable=False)
    discount_rate_pct = Column(Float, nullable=False)  # Discount percentage (e.g. 2.5%)
    apr_pct = Column(Float, nullable=False)            # Annualized Percentage Rate (e.g. 7.5%)
    tenor_days = Column(Integer, nullable=False)
    status = Column(String(50), default="EXTENDED")     # EXTENDED, ACCEPTED, DECLINED, EXPIRED
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="offers")
    financier = relationship("Financier", back_populates="offers")
    transactions = relationship("Transaction", back_populates="offer")


class MatchRecommendation(Base):
    __tablename__ = "match_recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    financier_id = Column(String(36), ForeignKey("financiers.id"), nullable=False)
    suitability_score = Column(Float, nullable=False) # 0-100 score
    is_eligible = Column(Boolean, default=True)
    calculated_apr_pct = Column(Float, nullable=False)
    explainability_reasons_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="match_recommendations")
    financier = relationship("Financier", back_populates="match_recommendations")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)
    offer_id = Column(String(36), ForeignKey("offers.id"), nullable=False)
    transaction_type = Column(String(50), nullable=False) # DISBURSEMENT, REPAYMENT, REBATE
    amount = Column(Float, nullable=False)
    sender_account = Column(String(255), nullable=False)
    recipient_account = Column(String(255), nullable=False)
    transaction_hash = Column(String(255), nullable=False)
    status = Column(String(50), default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="transactions")
    offer = relationship("Offer", back_populates="transactions")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False) # INVOICE, VERIFICATION, OFFER, FINANCING, SETTLEMENT
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")
