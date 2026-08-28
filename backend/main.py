import os
import mimetypes
import sqlalchemy
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Ensure proper MIME type mappings on all OS environments (e.g. Linux Docker/Render)
mimetypes.init()
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")

from backend.config import settings
from backend.database import get_db, engine, Base
from backend.models import User, Supplier, Buyer, Financier, Invoice, Offer, Transaction
from backend.schemas import SystemStatsResponse
from backend.auth.auth_service import get_current_user
from backend.security.rate_limiter import ai_rate_limiter

# Import all modular routers
from backend.auth.router import router as auth_router
from backend.invoices.router import router as invoices_router
from backend.verification.router import router as verification_router
from backend.risk.router import router as risk_router
from backend.matching.router import router as matching_router
from backend.offers.router import router as offers_router
from backend.financing.router import router as financing_router
from backend.settlement.router import router as settlement_router
from backend.notifications.router import router as notifications_router
from backend.admin.router import router as admin_router
from backend.reports.router import router as reports_router

# AI Agents
from ai.invoice_agent.agent import invoice_agent
from ai.risk_agent.agent import risk_agent
from ai.matching_agent.agent import matching_agent
from ai.offer_agent.agent import offer_agent
from ai.learning_agent.agent import learning_agent

# Ensure DB tables exist on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Supply Chain Finance System API",
    description="Strongly-typed Multi-Role Supply Chain Financing Platform with AI Autonomous Agents & Risk Models.",
    version="1.0.0"
)

# OWASP Security Headers & Static Asset MIME Type Middleware
@app.middleware("http")
async def add_security_headers_and_limit_size(request: Request, call_next):
    # 1. Payload size limit check (Max 2MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 2 * 1024 * 1024:
        return Response(content="Payload Too Large (Max 2MB)", status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    response = await call_next(request)

    # 2. Enforce strict Content-Type for static files to prevent nosniff block on Linux
    path = request.url.path.lower()
    if path.endswith(".css"):
        response.headers["Content-Type"] = "text/css; charset=utf-8"
    elif path.endswith(".js"):
        response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    elif path.endswith(".woff2"):
        response.headers["Content-Type"] = "font/woff2"

    # 3. OWASP Recommended Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
        "img-src 'self' data: https:;"
    )

    return response

# Hardened CORS configuration (Prevents credentials exposure on wildcard origins)
cors_origins = settings.cors_origins
allow_creds = False if "*" in cors_origins else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(invoices_router)
app.include_router(verification_router)
app.include_router(risk_router)
app.include_router(matching_router)
app.include_router(offers_router)
app.include_router(financing_router)
app.include_router(settlement_router)
app.include_router(notifications_router)
app.include_router(reports_router)

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(sqlalchemy.text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {e}"

    return {
        "status": "healthy",
        "system": settings.APP_NAME,
        "environment": settings.ENV,
        "database": db_status,
        "ai_agents_active": ["invoice_agent", "risk_agent", "matching_agent", "offer_agent", "learning_agent"]
    }

@app.get("/api/stats", response_model=SystemStatsResponse, tags=["Dashboard Analytics"])
def get_system_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_suppliers = db.query(Supplier).count()
    total_buyers = db.query(Buyer).count()
    total_financiers = db.query(Financier).count()
    
    invoices = db.query(Invoice).all()
    total_invoices_count = len(invoices)
    total_invoices_volume = sum(inv.amount for inv in invoices)
    
    total_funded_volume = sum(inv.amount for inv in invoices if inv.status in ["FINANCED", "SETTLED"])
    total_settled_volume = sum(inv.amount for inv in invoices if inv.status == "SETTLED")

    financiers = db.query(Financier).all()
    active_liquidity = sum(f.liquidity_pool for f in financiers)

    return SystemStatsResponse(
        total_users=total_users,
        total_suppliers=total_suppliers,
        total_buyers=total_buyers,
        total_financiers=total_financiers,
        total_invoices_count=total_invoices_count,
        total_invoices_volume=total_invoices_volume,
        total_funded_volume=total_funded_volume,
        total_settled_volume=total_settled_volume,
        active_liquidity_pool=active_liquidity
    )

@app.get("/api/directory/suppliers", tags=["Directory"])
def get_directory_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).all()
    return [
        {
            "id": s.id,
            "name": s.company_name or "Supplier",
            "company_name": s.company_name or "Supplier",
            "tax_id": s.tax_id or "TAX-UNSPECIFIED",
            "credit_rating": s.credit_rating or "BBB",
            "risk_score": s.risk_score if s.risk_score is not None else 25.0,
            "sector": "Industrial & Manufacturing Components",
            "rating": 4.8
        }
        for s in suppliers
    ]

@app.get("/api/directory/buyers", tags=["Directory"])
def get_directory_buyers(db: Session = Depends(get_db)):
    buyers = db.query(Buyer).all()
    return [
        {
            "id": b.id,
            "name": b.company_name or "Buyer",
            "company_name": b.company_name or "Buyer",
            "tax_id": b.tax_id or "TAX-UNSPECIFIED",
            "credit_rating": b.credit_rating or "AA",
            "max_credit_limit": b.max_credit_limit or 1000000.0
        }
        for b in buyers
    ]

@app.get("/api/directory/financiers", tags=["Directory"])
def get_directory_financiers(db: Session = Depends(get_db)):
    financiers = db.query(Financier).all()
    res = []
    for idx, f in enumerate(financiers):
        is_top = (idx == 0)
        min_apr = f.min_acceptable_apr or 5.0
        res.append({
            "id": f.id,
            "name": f.institution_name or "Institutional Financier",
            "institution_name": f.institution_name or "Institutional Financier",
            "liquidity_pool": f.liquidity_pool or 5000000.0,
            "min_acceptable_apr": min_apr,
            "max_risk_tolerance": f.max_risk_tolerance or 40.0,
            "rate": round(min_apr * 0.28, 1),
            "apr": min_apr,
            "speed": "Instant Payout" if is_top else "1-2 Business Days",
            "type": "Commercial Bank & NBFC",
            "score": 94 if is_top else max(75, 90 - idx * 5),
            "aiRec": is_top
        })
    return res

# Protected Direct AI Microservice endpoints
@app.post("/api/ai/invoice-parse", tags=["AI Agents"])
def parse_invoice_text(
    raw_text: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    ai_rate_limiter.check_rate_limit(request)
    return invoice_agent.parse_invoice_text(raw_text)

@app.post("/api/ai/evaluate-risk", tags=["AI Agents"])
def evaluate_risk(
    supplier_score: float,
    buyer_rating: str,
    amount: float,
    tenor_days: int,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    ai_rate_limiter.check_rate_limit(request)
    return risk_agent.evaluate_risk(supplier_score, buyer_rating, amount, tenor_days)

# Mount static frontend directory for root UI access
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
