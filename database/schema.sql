-- Supply Chain Finance System Database Schema
-- Standard SQL DDL for PostgreSQL / SQLite compatibility

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- supplier, buyer, financier, admin
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    tax_id VARCHAR(100) UNIQUE NOT NULL,
    credit_rating VARCHAR(10) DEFAULT 'BBB',
    risk_score FLOAT DEFAULT 25.0, -- Risk scale 0-100 (lower is better)
    total_funded_amount FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 3. Buyers Table
CREATE TABLE IF NOT EXISTS buyers (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    tax_id VARCHAR(100) UNIQUE NOT NULL,
    credit_rating VARCHAR(10) DEFAULT 'AA',
    max_credit_limit FLOAT DEFAULT 1000000.0,
    used_credit_limit FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 4. Financiers Table
CREATE TABLE IF NOT EXISTS financiers (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    liquidity_pool FLOAT DEFAULT 5000000.0,
    min_acceptable_apr FLOAT DEFAULT 5.0,
    max_risk_tolerance FLOAT DEFAULT 40.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 5. Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(36) PRIMARY KEY,
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id VARCHAR(36) NOT NULL,
    buyer_id VARCHAR(36) NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING_VERIFICATION', -- PENDING_VERIFICATION, VERIFIED, REJECTED, OFFER_EXTENDED, FINANCED, SETTLED
    description TEXT,
    document_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id),
    FOREIGN KEY (buyer_id) REFERENCES buyers (id)
);

-- 6. Verification Table
CREATE TABLE IF NOT EXISTS verification (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) UNIQUE NOT NULL,
    buyer_id VARCHAR(36) NOT NULL,
    verified_by_user_id VARCHAR(36) NOT NULL,
    is_valid BOOLEAN NOT NULL,
    verification_hash VARCHAR(255) NOT NULL,
    buyer_comments TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES buyers (id),
    FOREIGN KEY (verified_by_user_id) REFERENCES users (id)
);

-- 7. Offers Table
CREATE TABLE IF NOT EXISTS offers (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL,
    financier_id VARCHAR(36) NOT NULL,
    requested_amount FLOAT NOT NULL,
    offered_amount FLOAT NOT NULL,
    discount_rate_pct FLOAT NOT NULL, -- e.g., 2.5% discount
    apr_pct FLOAT NOT NULL,           -- Annualized Percentage Rate e.g. 7.5%
    tenor_days INT NOT NULL,
    status VARCHAR(50) DEFAULT 'EXTENDED', -- EXTENDED, ACCEPTED, DECLINED, EXPIRED
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE,
    FOREIGN KEY (financier_id) REFERENCES financiers (id)
);

-- 8. Transactions & Settlement Table
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL,
    offer_id VARCHAR(36) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- DISBURSEMENT, REPAYMENT, REBATE
    amount FLOAT NOT NULL,
    sender_account VARCHAR(255) NOT NULL,
    recipient_account VARCHAR(255) NOT NULL,
    transaction_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices (id),
    FOREIGN KEY (offer_id) REFERENCES offers (id)
);

-- 9. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR(50) NOT NULL, -- INVOICE, VERIFICATION, OFFER, FINANCING, SETTLEMENT
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
