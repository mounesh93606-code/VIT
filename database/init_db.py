import os
import sys
from datetime import date, datetime, timedelta

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import engine, SessionLocal, Base
from backend.models import User, Supplier, Buyer, Financier, Invoice, Verification, Offer, Transaction, Notification
from backend.auth.auth_service import hash_password

def init_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already contains seed data. Skipping seed step.")
            return

        print("Seeding initial users and entities...")
        pwd_hash = hash_password("Password123!")

        # 1. Admin User
        admin_user = User(
            email="admin@scf.com",
            hashed_password=pwd_hash,
            full_name="System Administrator",
            role="admin"
        )
        db.add(admin_user)

        # 2. Supplier User & Profile
        supplier_user = User(
            email="supplier@apex.com",
            hashed_password=pwd_hash,
            full_name="Apex Industrial Ltd",
            role="supplier"
        )
        db.add(supplier_user)
        db.flush()

        supplier_profile = Supplier(
            user_id=supplier_user.id,
            company_name="Apex Industrial Ltd",
            tax_id="TAX-SUP-APEX-998",
            credit_rating="A",
            risk_score=18.5,
            total_funded_amount=240000.0
        )
        db.add(supplier_profile)

        # 3. Buyer User & Profile
        buyer_user = User(
            email="buyer@globalcorp.com",
            hashed_password=pwd_hash,
            full_name="Global Retailers Inc",
            role="buyer"
        )
        db.add(buyer_user)
        db.flush()

        buyer_profile = Buyer(
            user_id=buyer_user.id,
            company_name="Global Retailers Inc",
            tax_id="TAX-BUY-GLOB-101",
            credit_rating="AA",
            max_credit_limit=5000000.0,
            used_credit_limit=350000.0
        )
        db.add(buyer_profile)

        # 4. Financier User & Profile
        financier_user = User(
            email="financier@horizon.com",
            hashed_password=pwd_hash,
            full_name="Horizon Capital Group",
            role="financier"
        )
        db.add(financier_user)
        db.flush()

        financier_profile = Financier(
            user_id=financier_user.id,
            institution_name="Horizon Capital Group",
            liquidity_pool=10000000.0,
            min_acceptable_apr=5.5,
            max_risk_tolerance=45.0
        )
        db.add(financier_profile)
        db.flush()

        # 5. Seed Invoices in Various Lifecycle States
        today = date.today()

        # Invoice 1: Pending Verification
        inv1 = Invoice(
            invoice_number="INV-2026-001",
            supplier_id=supplier_profile.id,
            buyer_id=buyer_profile.id,
            amount=150000.0,
            currency="USD",
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=50),
            status="PENDING_VERIFICATION",
            description="Shipment of 500 Heavy Industrial Components",
            document_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        db.add(inv1)

        # Invoice 2: Verified (Ready for Offers)
        inv2 = Invoice(
            invoice_number="INV-2026-002",
            supplier_id=supplier_profile.id,
            buyer_id=buyer_profile.id,
            amount=250000.0,
            currency="USD",
            issue_date=today - timedelta(days=15),
            due_date=today + timedelta(days=45),
            status="VERIFIED",
            description="Supply of Raw Precision Aluminum Materials",
            document_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        )
        db.add(inv2)
        db.flush()

        ver2 = Verification(
            invoice_id=inv2.id,
            buyer_id=buyer_profile.id,
            verified_by_user_id=buyer_user.id,
            is_valid=True,
            verification_hash="b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
            buyer_comments="Goods received in full compliance with PO-88492"
        )
        db.add(ver2)

        # Invoice 3: Financed (Disbursed)
        inv3 = Invoice(
            invoice_number="INV-2026-003",
            supplier_id=supplier_profile.id,
            buyer_id=buyer_profile.id,
            amount=100000.0,
            currency="USD",
            issue_date=today - timedelta(days=30),
            due_date=today + timedelta(days=30),
            status="FINANCED",
            description="Logistics and Freight Hardware Delivery",
            document_hash="7d837080e873b74551ce4e0169d41603fe45ee6bb3f3ee367a0184b0d2e54a2a"
        )
        db.add(inv3)
        db.flush()

        off3 = Offer(
            invoice_id=inv3.id,
            financier_id=financier_profile.id,
            requested_amount=100000.0,
            offered_amount=97500.0,
            discount_rate_pct=2.5,
            apr_pct=7.2,
            tenor_days=60,
            status="DISBURSED",
            expires_at=datetime.utcnow() + timedelta(days=3)
        )
        db.add(off3)

        # Welcome notifications
        db.add(Notification(
            user_id=supplier_user.id,
            title="Welcome to Supply Chain Finance",
            message="Your supplier account is active. You can now upload invoices and request early funding.",
            category="INVOICE"
        ))
        db.add(Notification(
            user_id=buyer_user.id,
            title="Pending Verification Alerts",
            message="You have 1 new invoice (INV-2026-001) awaiting buyer verification.",
            category="VERIFICATION"
        ))
        db.add(Notification(
            user_id=financier_user.id,
            title="Liquidity Pool Active",
            message="Your liquidity pool of $10,000,000 is ready. Verified invoice INV-2026-002 is open for bids.",
            category="OFFER"
        ))

        db.commit()
        print("Database initialized and populated with seed data successfully!")
    except Exception as e:
        db.rollback()
        print(f"Notice: Database initialization encountered existing schema or constraint notice: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
