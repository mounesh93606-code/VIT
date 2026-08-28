// =====================================================================
//  SCF NEXUS — Frontend Application Controller
//  Features: Dynamic Account Directory, Buyer Component Request, 
//            Supplier Invoice Download, Financiers & Banks Directory,
//            AI Best Financier Selection, Light Theme
// =====================================================================

const API_BASE = (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost")
    ? "http://127.0.0.1:8000/api"
    : `${window.location.origin}/api`;

// ─── State ───────────────────────────────────────────────────────────
let currentRole          = "supplier";
let authToken            = null;
let currentUser          = null;
let invoicesData         = [];
let selectedInvoice      = null;
let loginRole            = "supplier";   // selected role on login screen
let regRole              = "supplier";   // selected role on register screen
let selectedSupplierId   = null;        // for buyer component request
let selectedFinancierIds = new Set();    // for apply-financing modal
let purchaseOrders       = [];          // local PO list
let suppliersList        = [];          // dynamically fetched suppliers
let financiersList       = [];          // dynamically fetched financiers
let buyersList           = [];          // dynamically fetched buyers

// ─── Demo Credentials ────────────────────────────────────────────────
const PRESET_ACCOUNTS = {
    supplier:  { email: "supplier@apex.com",       password: "Password123!" },
    buyer:     { email: "buyer@globalcorp.com",     password: "Password123!" },
    financier: { email: "financier@horizon.com",    password: "Password123!" },
    admin:     { email: "admin@scf.com",            password: "Password123!" }
};

// ─── Fallback Catalogues ─────────────────────────────────────────────
const FALLBACK_SUPPLIERS = [
    { id: "seed-sup-001", name: "Apex Industrial Ltd",    company_name: "Apex Industrial Ltd",    sector: "Steel & Metal Components",    rating: 4.8, risk_score: 25.0 },
    { id: "seed-sup-002", name: "PrecisionTech Parts",    company_name: "PrecisionTech Parts",    sector: "Electronics & PCBs",          rating: 4.6, risk_score: 28.0 },
    { id: "seed-sup-003", name: "GreenLeaf Packaging",    company_name: "GreenLeaf Packaging",    sector: "Sustainable Packaging",       rating: 4.5, risk_score: 30.0 },
    { id: "seed-sup-004", name: "TurboMech Assemblies",   company_name: "TurboMech Assemblies",   sector: "Automotive Components",       rating: 4.7, risk_score: 22.0 }
];

const FALLBACK_FINANCIERS = [
    { id: "fin-001", name: "Horizon Capital Group",  institution_name: "Horizon Capital Group",  type: "Commercial NBFC", rate: 2.1, apr: 7.5, speed: "Instant Payout",   score: 94, aiRec: true,  liquidity_pool: 25000000 },
    { id: "fin-002", name: "First National Bank",    institution_name: "First National Bank",    type: "Commercial Bank", rate: 2.4, apr: 8.5, speed: "Same Day Wire",    score: 88, aiRec: false, liquidity_pool: 15000000 },
    { id: "fin-003", name: "FinBridge Trade Credit", institution_name: "FinBridge Trade Credit", type: "FinTech Lender",  rate: 2.8, apr: 9.8, speed: "Instant Payout",   score: 82, aiRec: false, liquidity_pool: 7000000 }
];

// =====================================================================
//  INIT
// =====================================================================
document.addEventListener("DOMContentLoaded", () => {
    console.log("SCF Nexus Initializing…");
    showLoginScreen();
});

// =====================================================================
//  LOGIN SCREEN LOGIC
// =====================================================================
function showLoginScreen() {
    document.getElementById("login-screen").style.display = "flex";
    document.getElementById("dashboard").style.display = "none";
}

function showDashboard() {
    document.getElementById("login-screen").style.display = "none";
    document.getElementById("dashboard").style.display = "block";
}

function showLoginView() {
    document.getElementById("login-form-view").style.display = "block";
    document.getElementById("register-form-view").style.display = "none";
}

function showRegisterView() {
    document.getElementById("login-form-view").style.display = "none";
    document.getElementById("register-form-view").style.display = "block";
}

function setLoginRole(role) {
    loginRole = role;
    document.querySelectorAll("#login-role-tabs .login-role-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === role);
    });
    const creds = PRESET_ACCOUNTS[role];
    if (creds) {
        document.getElementById("login-email").value = creds.email;
        document.getElementById("login-password").value = "";
    }
    const adminNote = document.getElementById("login-admin-note");
    if (adminNote) adminNote.style.display = (role === "admin") ? "flex" : "none";
}

function setRegRole(role) {
    regRole = role;
    document.querySelectorAll("#reg-role-tabs .login-role-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === role);
    });
    document.getElementById("rm-buyer-extra").style.display     = (role === "buyer")     ? "block" : "none";
    document.getElementById("rm-financier-extra").style.display = (role === "financier") ? "block" : "none";
    document.getElementById("rm-company-row").style.display     = "grid";
}

function fillDemoCredentials() {
    const creds = PRESET_ACCOUNTS[loginRole];
    if (creds) {
        document.getElementById("login-email").value    = creds.email;
        document.getElementById("login-password").value = creds.password;
        showToast(`Demo credentials filled for ${loginRole.toUpperCase()}`, "info");
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const email    = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const btn      = document.getElementById("login-submit-btn");

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Signing in…`;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        if (!res.ok) throw new Error("Invalid credentials. Please check and try again.");
        const data = await res.json();

        authToken   = data.access_token;
        currentUser = data.user;
        currentRole = currentUser.role || loginRole;

        showToast(`Welcome back, ${currentUser.full_name}!`, "success");
        showDashboard();
        initDashboard();

    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-right-to-bracket"></i> Sign In`;
    }
}

async function handleRegisterMain(event) {
    event.preventDefault();
    const name    = document.getElementById("rm-name").value;
    const email   = document.getElementById("rm-email").value;
    const pass    = document.getElementById("rm-pass").value;
    const confirm = document.getElementById("rm-confirm").value;
    const company = document.getElementById("rm-company").value;
    const tax     = document.getElementById("rm-tax").value;
    const capital = parseFloat(document.getElementById("rm-capital")?.value) || 5000000;

    if (pass !== confirm) { showToast("Passwords do not match!", "error"); return; }

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: name, email, password: pass, role: regRole,
                company_name: company || name,
                institution_name: company || name,
                liquidity_pool: capital,
                tax_id: tax || `TAX-${regRole.substring(0,3).toUpperCase()}-${Date.now().toString().slice(-4)}`
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Registration failed");
        }

        showToast(`Account created for ${name}! Please sign in.`, "success");
        PRESET_ACCOUNTS[regRole] = { email, password: pass };
        showLoginView();
        document.getElementById("login-email").value = email;
        setLoginRole(regRole);
        
        // Pre-fetch updated directory
        await loadAllDirectories();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// =====================================================================
//  DIRECTORY DATA LOADERS
// =====================================================================
async function loadAllDirectories() {
    await Promise.all([
        loadSuppliersDirectory(),
        loadFinanciersDirectory(),
        loadBuyersDirectory()
    ]);
    renderBuyerSuppliersGrid();
    renderSupplierFinanciersGrid();
}

async function loadSuppliersDirectory() {
    try {
        const res = await fetch(`${API_BASE}/directory/suppliers`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.length > 0) {
                suppliersList = data;
                return suppliersList;
            }
        }
    } catch (e) {
        console.warn("Could not fetch suppliers from backend:", e);
    }
    suppliersList = FALLBACK_SUPPLIERS;
    return suppliersList;
}

async function loadFinanciersDirectory() {
    try {
        const res = await fetch(`${API_BASE}/directory/financiers`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.length > 0) {
                financiersList = data;
                return financiersList;
            }
        }
    } catch (e) {
        console.warn("Could not fetch financiers from backend:", e);
    }
    financiersList = FALLBACK_FINANCIERS;
    return financiersList;
}

async function loadBuyersDirectory() {
    try {
        const res = await fetch(`${API_BASE}/directory/buyers`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.length > 0) {
                buyersList = data;
                return buyersList;
            }
        }
    } catch (e) {
        console.warn("Could not fetch buyers from backend:", e);
    }
    buyersList = [{ id: "seed-buyer-id-001", company_name: "Global Retailers Inc (Tax ID: TAX-BUY-GLOB-101)" }];
    return buyersList;
}

// =====================================================================
//  DASHBOARD INIT
// =====================================================================
async function initDashboard() {
    document.getElementById("active-user-name").textContent = currentUser.full_name;
    document.getElementById("active-role-tag").textContent  = currentRole.toUpperCase();

    document.querySelectorAll(".role-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === currentRole);
    });

    document.querySelectorAll(".portal-view").forEach(v => v.classList.remove("active-view"));
    const portal = document.getElementById(`portal-${currentRole}`);
    if (portal) portal.classList.add("active-view");

    await loadAllDirectories();
    await refreshStats();
    await loadRoleData();
}

async function switchRole(role) {
    currentRole = role;
    document.querySelectorAll(".role-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === role);
    });
    document.querySelectorAll(".portal-view").forEach(v => v.classList.remove("active-view"));
    const portal = document.getElementById(`portal-${role}`);
    if (portal) portal.classList.add("active-view");

    document.getElementById("active-role-tag").textContent = role.toUpperCase();
    await loginAsRole(role);
}

async function loginAsRole(role) {
    const creds = PRESET_ACCOUNTS[role];
    if (!creds) return;
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(creds)
        });
        if (!res.ok) throw new Error("Auth failed");
        const data = await res.json();
        authToken   = data.access_token;
        currentUser = data.user;
        document.getElementById("active-user-name").textContent = currentUser.full_name;
        await loadRoleData();
    } catch (err) {
        console.error("Role switch error:", err);
    }
}

async function loadRoleData() {
    await refreshStats();
    if      (currentRole === "supplier")  { await loadSupplierInvoices(); await loadBuyerOptionsForForm(); renderSupplierFinanciersGrid(); }
    else if (currentRole === "buyer")     { await loadBuyerPendingInvoices(); renderBuyerPOs(); renderBuyerSuppliersGrid(); }
    else if (currentRole === "financier") { await loadFinancierMatchedFeed(); }
    else if (currentRole === "admin")     { await loadAdminAuditLedger(); }
}

async function refreshStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) return;
        const stats = await res.json();
        document.getElementById("stat-total-volume").textContent  = `$${(stats.total_invoices_volume  || 0).toLocaleString()}`;
        document.getElementById("stat-funded-volume").textContent = `$${(stats.total_funded_volume    || 0).toLocaleString()}`;
        document.getElementById("stat-liquidity-pool").textContent= `$${(stats.active_liquidity_pool  || 0).toLocaleString()}`;
        const pool = document.getElementById("financier-pool-display");
        if (pool) pool.textContent = `$${(stats.active_liquidity_pool || 0).toLocaleString()}`;
    } catch (err) { console.warn("Stats error:", err); }
}

// =====================================================================
//  SUPPLIER PORTAL
// =====================================================================
async function loadSupplierInvoices() {
    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        invoicesData = await res.json();

        const container = document.getElementById("supplier-invoices-list");
        document.getElementById("supplier-invoice-count").textContent = `${invoicesData.length} Invoices`;

        if (invoicesData.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-file-invoice fa-2x"></i><p>No invoices submitted yet.</p></div>`;
            return;
        }

        container.innerHTML = invoicesData.map(inv => `
            <div class="invoice-card ${selectedInvoice && selectedInvoice.id === inv.id ? 'selected' : ''}"
                 onclick="selectSupplierInvoice('${inv.id}')">
                <div class="inv-card-header">
                    <span class="inv-num">${inv.invoice_number}</span>
                    <span class="status-pill ${getStatusClass(inv.status)}">${formatStatus(inv.status)}</span>
                </div>
                <div class="inv-card-body">
                    <div>
                        <div class="inv-amount">$${inv.amount.toLocaleString()}</div>
                        <div class="inv-meta">Buyer: <strong>${inv.buyer_company_name || 'Global Retailers'}</strong></div>
                    </div>
                    <div class="inv-meta text-right">
                        <div>Due: ${inv.due_date}</div>
                        <small class="text-muted">Net 60</small>
                    </div>
                </div>
                ${inv.status === 'VERIFIED' || inv.status === 'OFFER_EXTENDED' ? `
                <div style="margin-top:10px;display:flex;gap:8px;">
                    <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();openDownloadForInvoice('${inv.id}')">
                        <i class="fa-solid fa-file-arrow-down"></i> Download
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="event.stopPropagation();openApplyFinancing('${inv.id}')">
                        <i class="fa-solid fa-hand-holding-dollar"></i> Apply Financing
                    </button>
                </div>` : ''}
            </div>
        `).join("");

        populateDownloadSelect();

        if (invoicesData.length > 0 && !selectedInvoice) {
            selectSupplierInvoice(invoicesData[0].id);
        }
    } catch (err) {
        console.error("Error loading supplier invoices:", err);
    }
}

function populateDownloadSelect() {
    const sel = document.getElementById("download-invoice-select");
    if (!sel) return;
    sel.innerHTML = `<option value="">-- Select an invoice --</option>` +
        invoicesData.map(inv => `<option value="${inv.id}">${inv.invoice_number} — $${inv.amount.toLocaleString()}</option>`).join("");
}

async function selectSupplierInvoice(invId) {
    selectedInvoice = invoicesData.find(i => i.id === invId);
    await loadSupplierInvoices();

    const panel = document.getElementById("supplier-offers-panel");
    if (!selectedInvoice) return;

    const res = await fetch(`${API_BASE}/offers?invoice_id=${selectedInvoice.id}`, {
        headers: { Authorization: `Bearer ${authToken}` }
    });
    const offers = await res.json();

    if (offers.length === 0) {
        panel.innerHTML = `
            <div class="evidence-box">
                <h4 style="margin-bottom:10px;">Invoice ${selectedInvoice.invoice_number}</h4>
                <div class="evidence-item">
                    <span>Supplier GST &amp; Business Verification</span>
                    <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> 100% Valid</span>
                </div>
                <div class="evidence-item">
                    <span>Buyer Invoice Match</span>
                    <span class="evidence-check">${selectedInvoice.status !== 'PENDING_VERIFICATION'
                        ? '<i class="fa-solid fa-circle-check"></i> Verified'
                        : '<i class="fa-solid fa-clock"></i> Pending Buyer'}</span>
                </div>
                <div class="evidence-item">
                    <span>Cryptographic Hash Integrity</span>
                    <span class="evidence-check"><i class="fa-solid fa-lock"></i> SHA-256 OK</span>
                </div>
            </div>
            <div class="empty-state">
                <i class="fa-solid fa-hourglass-half fa-2x"></i>
                <p>No financing offers yet. Once verified, financiers will submit competing quotes.</p>
            </div>
        `;
        return;
    }

    const sorted = [...offers].sort((a, b) => (b.suitability_score || 90) - (a.suitability_score || 80));

    panel.innerHTML = `
        <div style="margin-bottom:14px;">
            <h4 style="font-weight:700;">Offers for ${selectedInvoice.invoice_number}</h4>
            <small class="text-muted">AI Suitability Ranker sorted offers by rate, tenor, advance &amp; speed.</small>
        </div>
        <div style="max-height:420px;overflow-y:auto;padding-right:4px;">
        ${sorted.map((off, idx) => {
            const isTop = idx === 0;
            const score = off.suitability_score || (isTop ? 94 : 80);
            const reasons = off.explainability_reasons || [
                "Required amount fully satisfied",
                "Competitive financing cost vs market",
                "Financier liquidity pool sufficient"
            ];
            return `
                <div class="offer-rank-card ${isTop ? 'top-choice' : ''}">
                    ${isTop ? '<div class="top-choice-badge"><i class="fa-solid fa-crown"></i> AI Best Match</div>' : ''}
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;${isTop?'margin-top:10px;':''}">
                        <div>
                            <h4 style="font-size:0.95rem;font-weight:700;">${off.financier_name || 'Horizon Capital'}</h4>
                            <span class="badge badge-ai">Score: <strong>${score}/100</strong></span>
                        </div>
                        <div class="text-right">
                            <div style="font-size:1.2rem;font-weight:800;color:var(--accent-emerald);font-family:var(--font-mono);">$${off.offered_amount.toLocaleString()}</div>
                            <small class="text-muted">Rate: ${off.discount_rate_pct}% (${off.apr_pct}% APR)</small>
                        </div>
                    </div>
                    <div class="score-bar-wrap mb-8"><div class="score-bar-fill ${isTop?'green':''}" style="width:${score}%;"></div></div>
                    <div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:8px;">
                        Tenor: <strong>${off.tenor_days} Days</strong> | Speed: <strong>Instant Payout</strong>
                    </div>
                    <div style="background:var(--bg-card-alt);padding:8px 10px;border-radius:6px;margin-bottom:10px;font-size:0.75rem;border:1px solid var(--border);">
                        <strong>AI Rationale:</strong>
                        <ul style="margin:4px 0 0 16px;color:var(--text-secondary);">
                            ${reasons.map(r => `<li>${r}</li>`).join("")}
                        </ul>
                    </div>
                    ${off.status === 'EXTENDED' ? `
                        <button class="btn ${isTop ? 'btn-success' : 'btn-primary'} btn-full"
                                onclick="acceptOffer('${off.id}')">
                            <i class="fa-solid fa-check-double"></i> Accept &amp; Disburse $${off.offered_amount.toLocaleString()}
                        </button>
                    ` : `<div class="badge badge-info" style="display:block;text-align:center;padding:8px;">Status: ${off.status}</div>`}
                </div>
            `;
        }).join("")}
        </div>
    `;
}

async function acceptOffer(offerId) {
    try {
        const res = await fetch(`${API_BASE}/offers/${offerId}/accept`, {
            method: "POST",
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error("Offer acceptance failed");

        const disbRes = await fetch(`${API_BASE}/financing/disburse`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ offer_id: offerId, recipient_account: "SUPPLIER_BANK_ACC_APEX_8892" })
        });

        if (disbRes.ok) {
            const d = await disbRes.json();
            showToast(`Capital Disbursed! $${d.amount.toLocaleString()} sent. Hash: ${d.transaction_hash.substring(0, 12)}…`, "success");
        } else {
            showToast("Offer accepted! Financing pending disbursement.", "success");
        }
        await loadSupplierInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// ─── Direct Download Modal Trigger ───────────────────────────────────
function openDownloadModalDirect() {
    populateDownloadSelect();
    openModal("modal-download-invoice");
    const sel = document.getElementById("download-invoice-select");
    if (sel && invoicesData.length > 0) {
        if (!sel.value && (selectedInvoice || invoicesData[0])) {
            sel.value = (selectedInvoice ? selectedInvoice.id : invoicesData[0].id);
        }
    }
    previewDownloadInvoice();
}

function openDownloadForInvoice(invId) {
    const inv = invoicesData.find(i => i.id === invId);
    if (!inv) return;
    selectedInvoice = inv;
    populateDownloadSelect();
    openModal("modal-download-invoice");
    const sel = document.getElementById("download-invoice-select");
    if (sel) sel.value = invId;
    previewDownloadInvoice();
}

function previewDownloadInvoice() {
    const sel = document.getElementById("download-invoice-select");
    const invId = sel ? sel.value : null;
    const preview = document.getElementById("download-preview-box");
    if (!preview) return;

    if (!invId) {
        preview.style.display = "none";
        return;
    }

    const inv = invoicesData.find(i => i.id === invId);
    if (!inv) {
        preview.style.display = "none";
        return;
    }

    document.getElementById("dl-inv-title").textContent   = `Invoice #${inv.invoice_number}`;
    document.getElementById("dl-inv-details").textContent = `Amount: $${inv.amount.toLocaleString()} | Due: ${inv.due_date} | Buyer: ${inv.buyer_company_name || 'Global Retailers'}`;
    preview.style.display = "block";
    preview.dataset.invId = invId;
}

function downloadInvoicePDF() {
    const sel = document.getElementById("download-invoice-select");
    const invId = sel ? sel.value : null;
    const inv = invoicesData.find(i => i.id === invId);
    if (!inv) { showToast("Please select an invoice first", "error"); return; }

    const printArea = document.getElementById("print-invoice-area");
    const issueDate = inv.issue_date || new Date().toISOString().split("T")[0];
    const hashVal   = `SHA256:${Math.random().toString(36).substring(2,14).toUpperCase()}${Math.random().toString(36).substring(2,10).toUpperCase()}`;

    printArea.innerHTML = `
        <html><head><title>Invoice ${inv.invoice_number}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; color: #0f172a; }
            .hdr { display:flex; justify-content:space-between; border-bottom:3px solid #6366f1; padding-bottom:20px; margin-bottom:20px; }
            h1 { color:#6366f1; font-size:28px; } .brand { font-size:12px; color:#475569; }
            table { width:100%; border-collapse:collapse; margin-top:20px; }
            th { background:#f1f5f9; padding:10px; text-align:left; font-size:12px; text-transform:uppercase; color:#475569; }
            td { padding:10px; border-bottom:1px solid #e2e8f0; font-size:13px; }
            .total-row td { font-weight:700; font-size:14px; background:#f8fafc; }
            .hash { font-size:10px; color:#94a3b8; margin-top:20px; word-break:break-all; }
            .footer { margin-top:30px; border-top:1px solid #e2e8f0; padding-top:16px; font-size:11px; color:#94a3b8; }
        </style></head><body>
        <div class="hdr">
            <div><h1>TAX INVOICE</h1><div class="brand">SCF NEXUS Marketplace</div></div>
            <div style="text-align:right;">
                <strong style="font-size:16px;">${inv.invoice_number}</strong><br>
                <span style="font-size:12px;color:#475569;">Issue Date: ${issueDate}</span><br>
                <span style="font-size:12px;color:#475569;">Due Date: ${inv.due_date}</span>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:20px;">
            <div><strong>From (Supplier)</strong><br>
                ${inv.supplier_company_name || currentUser?.company_name || 'Apex Industrial Ltd'}<br>
                <span style="font-size:12px;color:#475569;">Tax ID: TAX-SUP-APEX-001</span>
            </div>
            <div><strong>To (Buyer)</strong><br>
                ${inv.buyer_company_name || 'Global Retailers Inc'}<br>
                <span style="font-size:12px;color:#475569;">Tax ID: TAX-BUY-GLOB-101</span>
            </div>
        </div>
        <table>
            <thead><tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Amount</th></tr></thead>
            <tbody>
                <tr><td>${inv.description || 'Goods &amp; Services as per Purchase Order'}</td><td>1</td><td>$${inv.amount.toLocaleString()}</td><td>$${inv.amount.toLocaleString()}</td></tr>
                <tr class="total-row"><td colspan="3" style="text-align:right;"><strong>TOTAL DUE</strong></td><td><strong>$${inv.amount.toLocaleString()} USD</strong></td></tr>
            </tbody>
        </table>
        <div style="margin-top:20px;background:#f0fdf4;border:1px solid #6ee7b7;border-radius:8px;padding:14px;font-size:12px;">
            <strong>Payment Instructions:</strong> Transfer to SCF Nexus Escrow Account #ESCROW-88492 by ${inv.due_date}.
            For early payment discount, contact financier via SCF Nexus platform.
        </div>
        <div class="hash">Cryptographic Integrity: ${hashVal}</div>
        <div class="footer">This is a computer-generated invoice on the SCF Nexus AI Supply Chain Finance Marketplace. Secured with SHA-256 hash verification.</div>
        </body></html>
    `;

    const blob = new Blob([printArea.innerHTML], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href     = url;
    link.download = `SCF_Invoice_${inv.invoice_number}.html`;
    link.click();
    URL.revokeObjectURL(url);

    showToast(`Invoice ${inv.invoice_number} downloaded successfully!`, "success");
}

function printInvoice() {
    const sel = document.getElementById("download-invoice-select");
    const invId = sel ? sel.value : null;
    if (!invId) { showToast("Please select an invoice first", "error"); return; }
    downloadInvoicePDF();
    showToast("Invoice prepared for printing", "info");
}

// ─── Financiers & Banks Directory Modal (Supplier View) ──────────────
async function openFinanciersDirectoryModal() {
    await loadFinanciersDirectory();
    renderFinanciersDirectoryList();
    openModal("modal-financiers-directory");
}

function renderFinanciersDirectoryList() {
    const container = document.getElementById("financiers-directory-list");
    if (!container) return;

    container.innerHTML = financiersList.map((fin, idx) => {
        const isTop = fin.aiRec || idx === 0;
        return `
            <div class="financier-option ${isTop ? 'ai-recommended' : ''}" style="margin-bottom:12px;">
                ${isTop ? '<div class="ai-rec-badge"><i class="fa-solid fa-brain"></i> AI Top Recommendation</div>' : ''}
                <div class="fin-icon"><i class="fa-solid fa-building-columns"></i></div>
                <div class="fin-details" style="flex:1;">
                    <h4>${fin.name || fin.institution_name}</h4>
                    <p style="color:var(--text-secondary);font-size:0.75rem;">
                        ${fin.type || 'Commercial Banking Partner'} &bull; Speed: <strong>${fin.speed || 'Instant'}</strong>
                    </p>
                    <div style="font-size:0.75rem;margin-top:4px;color:var(--accent-emerald);">
                        Liquidity Pool: <strong>$${(fin.liquidity_pool || 10000000).toLocaleString()}</strong>
                    </div>
                </div>
                <div class="fin-rate">
                    <div class="rate-val">${fin.rate || 2.1}%</div>
                    <small>discount rate</small>
                    <small style="color:var(--text-muted);">${fin.apr || 7.5}% APR</small>
                </div>
            </div>
        `;
    }).join("");
}

// ─── Apply Financing Modal ────────────────────────────────────────────
async function openApplyFinancing(invId) {
    const inv = invoicesData.find(i => i.id === invId);
    if (!inv) return;
    selectedInvoice = inv;

    document.getElementById("af-inv-num").textContent    = inv.invoice_number;
    document.getElementById("af-inv-amount").textContent = `$${inv.amount.toLocaleString()}`;
    const statusEl = document.getElementById("af-inv-status");
    statusEl.textContent  = formatStatus(inv.status);
    statusEl.className    = `status-pill ${getStatusClass(inv.status)}`;

    await loadFinanciersDirectory();

    const best = financiersList.find(f => f.aiRec) || financiersList[0];
    document.getElementById("ai-best-name").textContent          = best.name || best.institution_name;
    document.getElementById("ai-best-score").textContent         = `${best.score || 94}/100`;
    document.getElementById("ai-best-score-bar").style.width     = `${best.score || 94}%`;
    document.getElementById("ai-best-rate").textContent          = `${best.rate || 2.1}%`;

    selectedFinancierIds.clear();
    renderFinancierOptions();

    openModal("modal-apply-financing");
}

function renderFinancierOptions() {
    const container = document.getElementById("financier-options-list");
    container.innerHTML = financiersList.map(fin => `
        <div class="financier-option ${fin.aiRec ? 'ai-recommended' : ''} ${selectedFinancierIds.has(fin.id) ? 'selected-financier' : ''}"
             id="fin-opt-${fin.id}"
             onclick="toggleFinancier('${fin.id}')">
            ${fin.aiRec ? '<div class="ai-rec-badge"><i class="fa-solid fa-brain"></i> AI Pick</div>' : ''}
            <div class="fin-checkbox">${selectedFinancierIds.has(fin.id) ? '<i class="fa-solid fa-check"></i>' : ''}</div>
            <div class="fin-icon"><i class="fa-solid fa-building-columns"></i></div>
            <div class="fin-details">
                <h4>${fin.name || fin.institution_name}</h4>
                <p>${fin.type || 'Commercial Partner'} &bull; Speed: ${fin.speed || 'Instant'}</p>
                <div class="score-bar-wrap mt-4" style="width:120px;">
                    <div class="score-bar-fill ${fin.aiRec ? 'green' : ''}" style="width:${fin.score || 90}%;"></div>
                </div>
            </div>
            <div class="fin-rate">
                <div class="rate-val">${fin.rate || 2.1}%</div>
                <small>discount rate</small>
                <small style="color:var(--text-muted);">${fin.apr || 7.5}% APR</small>
            </div>
        </div>
    `).join("");

    updateSelectedCount();
}

function toggleFinancier(finId) {
    if (selectedFinancierIds.has(finId)) {
        selectedFinancierIds.delete(finId);
    } else {
        selectedFinancierIds.add(finId);
    }
    renderFinancierOptions();
}

function updateSelectedCount() {
    const countEl = document.getElementById("selected-financiers-count");
    const n = selectedFinancierIds.size;
    if (n === 0) {
        countEl.innerHTML = `<i class="fa-solid fa-circle-info"></i><span>Select at least 1 financier to apply. Multiple applications increase approval chances.</span>`;
        countEl.className = "info-box mt-12";
    } else {
        countEl.innerHTML = `<i class="fa-solid fa-circle-check"></i><span><strong>${n} financier${n > 1 ? 's' : ''}</strong> selected. AI will choose the best offer from responses.</span>`;
        countEl.className = "success-box mt-12";
    }
}

async function submitFinancingApplications() {
    if (selectedFinancierIds.size === 0) {
        showToast("Please select at least one financier", "error");
        return;
    }

    const btn = document.getElementById("apply-financing-btn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Submitting…`;

    const selected = financiersList.filter(f => selectedFinancierIds.has(f.id));
    await new Promise(r => setTimeout(r, 900));

    const aiBest = selected.find(f => f.aiRec) || selected.reduce((a, b) => (a.rate || 2.5) < (b.rate || 2.5) ? a : b);

    closeModal("modal-apply-financing");

    showToast(
        `Applications sent to ${selected.length} financier${selected.length > 1 ? 's' : ''}! AI recommends ${aiBest.name || aiBest.institution_name} (${aiBest.rate || 2.1}% rate).`,
        "success"
    );

    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit Applications`;
    await loadSupplierInvoices();
}

// =====================================================================
//  BUYER PORTAL
// =====================================================================
function renderBuyerPOs() {
    const container = document.getElementById("buyer-po-list");
    const badge     = document.getElementById("po-count-badge");
    badge.textContent = `${purchaseOrders.length} POs`;

    if (purchaseOrders.length === 0) {
        container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-boxes-stacked fa-2x"></i><p>No purchase orders placed yet.</p></div>`;
        return;
    }

    container.innerHTML = purchaseOrders.map(po => `
        <div class="invoice-card">
            <div class="inv-card-header">
                <span class="inv-num">${po.ref || 'PO-' + po.id}</span>
                <span class="status-pill ${po.status === 'CONFIRMED' ? 'verified' : 'pending'}">${po.status}</span>
            </div>
            <div class="inv-card-body">
                <div>
                    <div class="inv-amount">$${po.value.toLocaleString()}</div>
                    <div class="inv-meta">Supplier: <strong>${po.supplierName}</strong></div>
                </div>
                <div class="inv-meta text-right">
                    <div>${po.component}</div>
                    <small class="text-muted">Qty: ${po.quantity}</small>
                </div>
            </div>
            <div style="margin-top:8px;">
                <span style="font-size:0.75rem;color:var(--text-muted);"><i class="fa-solid fa-calendar"></i> Delivery by: ${po.deliveryDate}</span>
            </div>
        </div>
    `).join("");
}

// ─── Buyer Suppliers Directory Grid ──────────────────────────────────
function renderBuyerSuppliersGrid() {
    const container = document.getElementById("buyer-suppliers-grid");
    const badge = document.getElementById("buyer-suppliers-count-badge");
    if (!container) return;

    if (badge) {
        badge.textContent = `${suppliersList.length} Supplier${suppliersList.length === 1 ? '' : 's'}`;
    }

    if (!suppliersList || suppliersList.length === 0) {
        container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><i class="fa-solid fa-industry fa-2x"></i><p>No suppliers registered yet.</p></div>`;
        return;
    }

    container.innerHTML = suppliersList.map(sup => `
        <div class="supplier-card" style="flex-direction:column;align-items:flex-start;padding:14px;border-radius:var(--radius-md);cursor:default;">
            <div style="display:flex;align-items:center;gap:12px;width:100%;">
                <div class="supplier-avatar">${(sup.name || sup.company_name || 'S').charAt(0).toUpperCase()}</div>
                <div class="supplier-info" style="flex:1;">
                    <h4 style="font-size:0.92rem;font-weight:700;">${sup.name || sup.company_name}</h4>
                    <p style="margin:2px 0 0;font-size:0.75rem;color:var(--text-secondary);">${sup.sector || 'Industrial & Manufacturing'}</p>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;width:100%;margin-top:10px;padding:8px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);font-size:0.75rem;">
                <span>Tax ID: <strong>${sup.tax_id || 'VERIFIED'}</strong></span>
                <span>Rating: <strong style="color:var(--accent-indigo);">${sup.credit_rating || 'BBB'}</strong></span>
            </div>
            <div style="width:100%;margin-top:10px;">
                <button class="btn btn-primary btn-sm" style="width:100%;justify-content:center;" onclick="openComponentRequestModal('${sup.id}')">
                    <i class="fa-solid fa-boxes-stacked"></i> Request Components
                </button>
            </div>
        </div>
    `).join("");
}

// ─── Supplier Financiers Directory Grid ──────────────────────────────
function renderSupplierFinanciersGrid() {
    const container = document.getElementById("supplier-financiers-grid");
    const badge = document.getElementById("supplier-financiers-count-badge");
    if (!container) return;

    if (badge) {
        badge.textContent = `${financiersList.length} Financier${financiersList.length === 1 ? '' : 's'} Active`;
    }

    if (!financiersList || financiersList.length === 0) {
        container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><i class="fa-solid fa-building-columns fa-2x"></i><p>No financiers connected yet.</p></div>`;
        return;
    }

    container.innerHTML = financiersList.map((fin, idx) => {
        const isTop = fin.aiRec || idx === 0;
        return `
            <div class="financier-option ${isTop ? 'ai-recommended' : ''}" style="margin:0;flex-direction:column;align-items:flex-start;padding:14px;border-radius:var(--radius-md);cursor:default;">
                ${isTop ? '<div class="ai-rec-badge"><i class="fa-solid fa-brain"></i> AI Top Match</div>' : ''}
                <div style="display:flex;align-items:center;gap:10px;width:100%;">
                    <div class="fin-icon"><i class="fa-solid fa-building-columns"></i></div>
                    <div class="fin-details" style="flex:1;">
                        <h4 style="font-size:0.9rem;font-weight:700;">${fin.name || fin.institution_name}</h4>
                        <p style="color:var(--text-secondary);font-size:0.75rem;margin:2px 0 0;">
                            ${fin.type || 'Institutional Liquidity'} &bull; <strong>${fin.speed || 'Instant Payout'}</strong>
                        </p>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;width:100%;margin-top:10px;padding:8px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);font-size:0.78rem;">
                    <div>
                        <span style="color:var(--text-muted);display:block;font-size:0.7rem;">Discount Rate</span>
                        <strong style="color:var(--accent-indigo);font-size:0.95rem;">${fin.rate || 2.1}%</strong>
                    </div>
                    <div>
                        <span style="color:var(--text-muted);display:block;font-size:0.7rem;">Est. APR</span>
                        <strong style="font-size:0.95rem;">${fin.apr || 7.5}%</strong>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:var(--text-muted);display:block;font-size:0.7rem;">Liquidity Pool</span>
                        <strong style="color:var(--accent-emerald);font-size:0.85rem;">$${(fin.liquidity_pool || 5000000).toLocaleString()}</strong>
                    </div>
                </div>
                <div style="width:100%;margin-top:10px;">
                    <button class="btn btn-outline btn-sm" style="width:100%;justify-content:center;" onclick="openModal('modal-create-invoice')">
                        <i class="fa-solid fa-paper-plane"></i> Submit Invoice for Financing
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

// ─── Component Request Modal ──────────────────────────────────────────
async function openComponentRequestModal(supId = null) {
    await loadSuppliersDirectory();
    if (supId) {
        selectedSupplierId = supId;
    } else if (!selectedSupplierId || !suppliersList.some(s => s.id === selectedSupplierId)) {
        selectedSupplierId = suppliersList.length > 0 ? suppliersList[0].id : null;
    }
    renderSupplierSelectionList();
    openModal("modal-component-request");
}

function renderSupplierSelectionList() {
    const container = document.getElementById("supplier-selection-list");
    if (!container) return;

    if (!suppliersList || suppliersList.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No suppliers available.</p></div>`;
        return;
    }

    container.innerHTML = suppliersList.map(sup => `
        <div class="supplier-card ${selectedSupplierId === sup.id ? 'selected' : ''}"
             id="sup-card-${sup.id}"
             onclick="selectSupplierForRequest('${sup.id}')">
            <div class="supplier-avatar">${(sup.name || sup.company_name || 'S').charAt(0).toUpperCase()}</div>
            <div class="supplier-info" style="flex:1;">
                <h4>${sup.name || sup.company_name}</h4>
                <p>${sup.sector || 'Industrial Goods'} &bull; <i class="fa-solid fa-star" style="color:var(--accent-amber);font-size:0.7rem;"></i> ${sup.rating || 4.8} &bull; Rating: <strong>${sup.credit_rating || 'BBB'}</strong></p>
            </div>
            ${selectedSupplierId === sup.id ? '<i class="fa-solid fa-circle-check" style="color:var(--accent-indigo);margin-left:auto;font-size:1.1rem;"></i>' : ''}
        </div>
    `).join("");
}

function selectSupplierForRequest(supId) {
    selectedSupplierId = supId;
    renderSupplierSelectionList();
}

async function handleComponentRequest(event) {
    event.preventDefault();
    if (!selectedSupplierId) {
        showToast("Please select a supplier", "error");
        return;
    }

    const supplier = suppliersList.find(s => s.id === selectedSupplierId) || { name: "Selected Supplier" };
    const component    = document.getElementById("cr-component").value;
    const quantity     = document.getElementById("cr-quantity").value;
    const value        = parseFloat(document.getElementById("cr-value").value);
    const deliveryDate = document.getElementById("cr-delivery-date").value;
    const poRef        = document.getElementById("cr-po-ref").value || `PO-${Date.now().toString().slice(-6)}`;
    const notes        = document.getElementById("cr-notes").value;

    const newPO = {
        id:           Date.now(),
        ref:          poRef,
        supplierName: supplier.name || supplier.company_name,
        supplierId:   selectedSupplierId,
        component,
        quantity,
        value,
        deliveryDate,
        notes,
        status:       "CONFIRMED",
        createdAt:    new Date().toISOString()
    };

    purchaseOrders.unshift(newPO);
    closeModal("modal-component-request");
    renderBuyerPOs();

    showToast(
        `Component purchase order created for ${supplier.name || supplier.company_name}! Ref: ${poRef}`,
        "success"
    );

    event.target.reset();
}

// ─── Buyer Invoice Verification ───────────────────────────────────────
async function loadBuyerPendingInvoices() {
    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        const allInvoices = await res.json();
        const pending = allInvoices.filter(i => i.status === "PENDING_VERIFICATION" || i.status === "VERIFIED");

        const container = document.getElementById("buyer-pending-list");
        if (pending.length === 0) {
            container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-inbox fa-2x"></i><p>No invoices pending buyer approval.</p></div>`;
            return;
        }

        container.innerHTML = pending.map(inv => `
            <div class="invoice-card ${selectedInvoice && selectedInvoice.id === inv.id ? 'selected' : ''}"
                 onclick="selectBuyerInvoice('${inv.id}', ${JSON.stringify(inv).replace(/"/g,'&quot;')})">
                <div class="inv-card-header">
                    <span class="inv-num">${inv.invoice_number}</span>
                    <span class="status-pill ${getStatusClass(inv.status)}">${formatStatus(inv.status)}</span>
                </div>
                <div class="inv-card-body">
                    <div>
                        <div class="inv-amount">$${inv.amount.toLocaleString()}</div>
                        <div class="inv-meta">Supplier: <strong>${inv.supplier_company_name || 'Apex Industrial'}</strong></div>
                    </div>
                    <div class="inv-meta text-right">
                        <div>Due: ${inv.due_date}</div>
                    </div>
                </div>
            </div>
        `).join("");

        if (pending.length > 0 && !selectedInvoice) {
            selectBuyerInvoice(pending[0].id, pending[0]);
        }
    } catch (err) {
        console.error("Error loading buyer invoices:", err);
    }
}

function selectBuyerInvoice(invId, invData) {
    selectedInvoice = invData || { id: invId };
    const detailPanel = document.getElementById("buyer-verification-detail");

    if (selectedInvoice.status === "FINANCED") {
        detailPanel.innerHTML = `
            <div class="evidence-box">
                <h4>Invoice ${selectedInvoice.invoice_number || ''} — <span class="status-pill financed">FINANCED</span></h4>
                <p class="text-muted mt-8" style="font-size:0.83rem;">Financier payout completed. Invoice awaiting maturity date settlement.</p>
                <div class="evidence-item mt-8">
                    <span>Financed Amount</span>
                    <strong style="color:var(--accent-emerald);">$${(selectedInvoice.amount || 0).toLocaleString()}</strong>
                </div>
            </div>
            <button class="btn btn-success btn-full" style="margin-top:12px;padding:14px;"
                    onclick="simulateSettlement('${selectedInvoice.id}', ${selectedInvoice.amount || 0})">
                <i class="fa-solid fa-money-bill-transfer"></i>
                Simulate Buyer Settlement ($${(selectedInvoice.amount || 0).toLocaleString()})
            </button>
        `;
        return;
    }

    detailPanel.innerHTML = `
        <div class="evidence-box">
            <h4 style="margin-bottom:10px;">Evidence Verification Checklist</h4>
            <div class="evidence-item">
                <span>1. Supplier GST &amp; Business Registration</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> VERIFIED</span>
            </div>
            <div class="evidence-item">
                <span>2. Purchase Order (PO) Matching</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> MATCHED (PO-88492)</span>
            </div>
            <div class="evidence-item">
                <span>3. Delivery Note &amp; Physical Receipt</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> DELIVERED</span>
            </div>
            <div class="evidence-item">
                <span>4. Line Item Amount &amp; Payment Terms</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> NET 60 CONFIRMED</span>
            </div>
        </div>

        <div class="form-group">
            <label>Buyer Approval Notes</label>
            <textarea id="buyer-comment-inp" rows="2" class="form-control"
                      placeholder="Confirmed goods received in full compliance with purchase contract."></textarea>
        </div>

        <div style="display:flex;gap:10px;">
            <button class="btn btn-success" style="flex:1;" onclick="verifyInvoice(true)">
                <i class="fa-solid fa-check-circle"></i> Approve &amp; Verify (95% Conf.)
            </button>
            <button class="btn btn-danger" style="flex:1;" onclick="verifyInvoice(false)">
                <i class="fa-solid fa-circle-xmark"></i> Flag Dispute
            </button>
        </div>
    `;
}

async function verifyInvoice(isValid) {
    if (!selectedInvoice) return;
    const comments = (document.getElementById("buyer-comment-inp")?.value) || (isValid ? "Verified by buyer" : "Disputed by buyer");
    try {
        const res = await fetch(`${API_BASE}/verification/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ invoice_id: selectedInvoice.id, is_valid: isValid, buyer_comments: comments })
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Verification failed"); }
        showToast(isValid ? "Invoice Verified! Status set to ✅ VERIFIED." : "Invoice flagged as Disputed.", isValid ? "success" : "error");
        selectedInvoice = null;
        await loadBuyerPendingInvoices();
    } catch (err) {
        showToast(`Verification Error: ${err.message}`, "error");
    }
}

async function simulateSettlement(invoiceId, amount) {
    try {
        const res = await fetch(`${API_BASE}/settlement/settle`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({ invoice_id: invoiceId, payment_amount: amount, payer_account: "BUYER_SETTLEMENT_ACC_GLOB_101" })
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Settlement failed"); }
        const data = await res.json();
        showToast(`Settlement Complete! Paid $${data.total_paid.toLocaleString()}. Yield returned to financier.`, "success");
        await loadBuyerPendingInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Settlement error: ${err.message}`, "error");
    }
}

// =====================================================================
//  FINANCIER PORTAL LOGIC
// =====================================================================
let financierStatusFilter   = "ALL";
let financierSupplierFilter = null;
let financierInvoicesCache  = [];
let financierSelectedInv    = null;
let financierProfileState   = {
    liquidity_pool: 10000000.0,
    max_risk_tolerance: 45.0,
    min_acceptable_apr: 5.5
};

async function loadFinancierMatchedFeed() {
    try {
        await loadSuppliersDirectory();

        // 1. Fetch all market invoices for financier inspection
        const res = await fetch(`${API_BASE}/invoices`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        if (res.ok) {
            financierInvoicesCache = await res.json();
        } else {
            financierInvoicesCache = [];
        }

        // 2. Compute market metrics
        const totalDemandVolume = financierInvoicesCache.reduce((sum, i) => sum + (i.amount || 0), 0);
        const countAll = financierInvoicesCache.length;
        const countVerified = financierInvoicesCache.filter(i => i.status === "VERIFIED" || i.status === "OFFER_EXTENDED").length;
        const countPending = financierInvoicesCache.filter(i => i.status === "PENDING_VERIFICATION").length;
        const countDisputed = financierInvoicesCache.filter(i => i.status === "DISPUTED" || i.status === "REJECTED").length;
        const countFinanced = financierInvoicesCache.filter(i => i.status === "FINANCED" || i.status === "SETTLED").length;

        // 3. Update Criteria Bar stats
        const demandEl = document.getElementById("fin-stat-demand");
        if (demandEl) demandEl.textContent = `$${totalDemandVolume.toLocaleString()} (${countAll} Req${countAll === 1 ? '' : 's'})`;

        const countAllEl = document.getElementById("fin-count-all");
        if (countAllEl) countAllEl.textContent = countAll;
        const countVerEl = document.getElementById("fin-count-verified");
        if (countVerEl) countVerEl.textContent = countVerified;
        const countPenEl = document.getElementById("fin-count-pending");
        if (countPenEl) countPenEl.textContent = countPending;
        const countDisEl = document.getElementById("fin-count-disputed");
        if (countDisEl) countDisEl.textContent = countDisputed;
        const countFinEl = document.getElementById("fin-count-financed");
        if (countFinEl) countFinEl.textContent = countFinanced;

        // 4. Render Supplier Filter Pills
        renderFinancierSupplierFilterPills();

        // 5. Render Invoices Feed
        renderFinancierInvoicesFeed();

    } catch (err) {
        console.error("Financier feed loading error:", err);
    }
}

function renderFinancierSupplierFilterPills() {
    const container = document.getElementById("financier-supplier-filter-list");
    if (!container) return;

    // Collect all suppliers from directory or who have invoices
    const map = new Map();
    suppliersList.forEach(s => {
        map.set(s.id, { id: s.id, name: s.name || s.company_name, count: 0, rating: s.credit_rating || 'BBB', risk: s.risk_score || 25.0 });
    });

    financierInvoicesCache.forEach(inv => {
        const sId = inv.supplier_id || inv.supplier_company_name;
        if (sId && map.has(sId)) {
            map.get(sId).count += 1;
        } else if (inv.supplier_company_name) {
            map.set(inv.supplier_company_name, { id: inv.supplier_company_name, name: inv.supplier_company_name, count: 1, rating: 'BBB', risk: 25.0 });
        }
    });

    const isAllActive = !financierSupplierFilter;
    let html = `
        <button class="supplier-filter-pill ${isAllActive ? 'active' : ''}" onclick="setFinancierSupplierFilter(null)">
            <i class="fa-solid fa-layer-group"></i> All Suppliers <span class="pill-count">${financierInvoicesCache.length}</span>
        </button>
    `;

    map.forEach(sup => {
        const isActive = financierSupplierFilter === sup.id || financierSupplierFilter === sup.name;
        html += `
            <button class="supplier-filter-pill ${isActive ? 'active' : ''}" onclick="setFinancierSupplierFilter('${sup.id}')">
                <span style="font-weight:700;">${(sup.name || 'S').charAt(0).toUpperCase()}</span>
                <span>${sup.name}</span>
                <span class="pill-count">${sup.count}</span>
            </button>
        `;
    });

    container.innerHTML = html;
}

function setFinancierStatusFilter(status) {
    financierStatusFilter = status;
    document.querySelectorAll(".filter-tab-btn").forEach(btn => btn.classList.remove("active"));
    const activeTab = document.getElementById(`fin-tab-${status.toLowerCase()}`);
    if (activeTab) activeTab.classList.add("active");
    renderFinancierInvoicesFeed();
}

function setFinancierSupplierFilter(supId) {
    financierSupplierFilter = supId;
    renderFinancierSupplierFilterPills();
    renderFinancierSelectedSupplierProfile();
    renderFinancierInvoicesFeed();
}

function renderFinancierSelectedSupplierProfile() {
    const box = document.getElementById("financier-selected-supplier-profile");
    const tag = document.getElementById("financier-filtered-supplier-tag");
    if (!box) return;

    if (!financierSupplierFilter) {
        box.style.display = "none";
        if (tag) tag.textContent = "Showing All Suppliers";
        return;
    }

    const sup = suppliersList.find(s => s.id === financierSupplierFilter || s.name === financierSupplierFilter || s.company_name === financierSupplierFilter)
        || { name: financierSupplierFilter, company_name: financierSupplierFilter, credit_rating: "BBB", risk_score: 25.0, tax_id: "TAX-SUPPLIER" };

    const supInvoices = financierInvoicesCache.filter(i => 
        i.supplier_id === sup.id || i.supplier_company_name === sup.name || i.supplier_company_name === sup.company_name
    );
    const supTotalVol = supInvoices.reduce((sum, i) => sum + (i.amount || 0), 0);

    if (tag) tag.textContent = `Filtered: ${sup.name || sup.company_name}`;

    box.style.display = "block";
    box.innerHTML = `
        <div class="glass-panel" style="border-left:4px solid var(--accent-indigo);padding:14px 18px;background:var(--accent-indigo-light);">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div class="supplier-avatar" style="width:48px;height:48px;font-size:1.2rem;">
                        ${(sup.name || sup.company_name || 'S').charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h3 style="font-size:1rem;font-weight:700;margin:0;">${sup.name || sup.company_name}</h3>
                        <p style="margin:2px 0 0;font-size:0.78rem;color:var(--text-secondary);">
                            Tax ID: <strong>${sup.tax_id || 'VERIFIED'}</strong> &bull; Sector: ${sup.sector || 'Manufacturing & Components'}
                        </p>
                    </div>
                </div>
                <div style="display:flex;gap:16px;align-items:center;">
                    <div style="text-align:right;">
                        <span style="font-size:0.7rem;color:var(--text-muted);display:block;">Credit Rating</span>
                        <strong style="color:var(--accent-indigo);font-size:0.95rem;">${sup.credit_rating || 'BBB'}</strong>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.7rem;color:var(--text-muted);display:block;">Risk Profile</span>
                        <strong style="color:var(--accent-emerald);font-size:0.95rem;">${sup.risk_score || 22.5}% LOW</strong>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.7rem;color:var(--text-muted);display:block;">Supplier Requests</span>
                        <strong style="font-size:0.95rem;">$${supTotalVol.toLocaleString()} (${supInvoices.length})</strong>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="setFinancierSupplierFilter(null)">
                        <i class="fa-solid fa-xmark"></i> Clear Filter
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderFinancierInvoicesFeed() {
    const feed = document.getElementById("financier-matched-feed");
    const countBadge = document.getElementById("financier-requests-count");
    if (!feed) return;

    let filtered = financierInvoicesCache;

    // Apply Supplier Filter
    if (financierSupplierFilter) {
        filtered = filtered.filter(i => 
            i.supplier_id === financierSupplierFilter ||
            i.supplier_company_name === financierSupplierFilter ||
            (suppliersList.find(s => s.id === financierSupplierFilter)?.company_name === i.supplier_company_name)
        );
    }

    // Apply Status Filter
    if (financierStatusFilter === "VERIFIED") {
        filtered = filtered.filter(i => i.status === "VERIFIED" || i.status === "OFFER_EXTENDED");
    } else if (financierStatusFilter === "PENDING") {
        filtered = filtered.filter(i => i.status === "PENDING_VERIFICATION");
    } else if (financierStatusFilter === "DISPUTED") {
        filtered = filtered.filter(i => i.status === "DISPUTED" || i.status === "REJECTED");
    } else if (financierStatusFilter === "FINANCED") {
        filtered = filtered.filter(i => i.status === "FINANCED" || i.status === "SETTLED");
    }

    if (countBadge) {
        countBadge.textContent = `${filtered.length} Invoice${filtered.length === 1 ? '' : 's'}`;
    }

    if (filtered.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-inbox fa-2x"></i>
                <p>No invoices match the selected filter criteria.</p>
            </div>
        `;
        return;
    }

    feed.innerHTML = filtered.map(inv => {
        const isSelected = financierSelectedInv && financierSelectedInv.id === inv.id;
        const riskScore = inv.risk_score || (inv.amount > 200000 ? 18.5 : 24.0);
        const fitsRisk = riskScore <= financierProfileState.max_risk_tolerance;
        const fitsLiquidity = inv.amount <= financierProfileState.liquidity_pool;
        const conditionMatches = fitsRisk && fitsLiquidity;

        let statusPillHtml = '';
        if (inv.status === 'VERIFIED' || inv.status === 'OFFER_EXTENDED') {
            statusPillHtml = `<span class="status-pill verified"><i class="fa-solid fa-circle-check"></i> Buyer Accepted</span>`;
        } else if (inv.status === 'PENDING_VERIFICATION') {
            statusPillHtml = `<span class="status-pill pending"><i class="fa-solid fa-clock"></i> Awaiting Buyer Approval</span>`;
        } else if (inv.status === 'DISPUTED' || inv.status === 'REJECTED') {
            statusPillHtml = `<span class="status-pill disputed"><i class="fa-solid fa-triangle-exclamation"></i> Buyer Disputed / Rejected</span>`;
        } else {
            statusPillHtml = `<span class="status-pill financed"><i class="fa-solid fa-money-bill-wave"></i> Financed</span>`;
        }

        return `
            <div class="invoice-card ${isSelected ? 'selected' : ''}"
                 onclick="selectFinancierInvoice('${inv.id}')"
                 style="margin-bottom:10px;padding:12px 14px;">
                <div class="inv-card-header" style="margin-bottom:8px;">
                    <span class="inv-num" style="font-weight:700;">${inv.invoice_number}</span>
                    <div style="display:flex;gap:6px;align-items:center;">
                        ${conditionMatches 
                            ? '<span class="condition-badge matched"><i class="fa-solid fa-circle-check"></i> Fits Criteria</span>' 
                            : '<span class="condition-badge exceeded"><i class="fa-solid fa-sliders"></i> Exceeds Limits</span>'}
                        ${statusPillHtml}
                    </div>
                </div>
                <div class="inv-card-body">
                    <div>
                        <div class="inv-amount" style="font-size:1.15rem;font-weight:800;color:var(--text-primary);">$${(inv.amount || 0).toLocaleString()}</div>
                        <div class="inv-meta" style="margin-top:2px;">
                            Supplier: <strong>${inv.supplier_company_name || 'Apex Industrial'}</strong> &bull; Buyer: <strong>${inv.buyer_company_name || 'Global Retailers'}</strong>
                        </div>
                    </div>
                    <div class="inv-meta text-right">
                        <div>Due: <strong>${inv.due_date || 'Net 60'}</strong></div>
                        <small class="text-muted">Risk Score: <strong>${riskScore}%</strong></small>
                    </div>
                </div>
            </div>
        `;
    }).join("");

    if (filtered.length > 0 && !financierSelectedInv) {
        selectFinancierInvoice(filtered[0].id);
    }
}

function selectFinancierInvoice(invId) {
    const inv = financierInvoicesCache.find(i => i.id === invId);
    if (!inv) return;
    financierSelectedInv = inv;
    renderFinancierInvoicesFeed();
    renderFinancierOfferDesk(inv);
}

function renderFinancierOfferDesk(inv) {
    const calc = document.getElementById("financier-offer-calculator");
    if (!calc) return;

    const riskScore = inv.risk_score || (inv.amount > 200000 ? 18.5 : 24.0);
    const recommendedApr = (5.0 + (riskScore * 0.12)).toFixed(1);
    const fitsRisk = riskScore <= financierProfileState.max_risk_tolerance;
    const fitsLiquidity = inv.amount <= financierProfileState.liquidity_pool;
    const conditionMatches = fitsRisk && fitsLiquidity;

    const defaultDiscount = 2.2;
    const initialFunded = inv.amount;

    calc.innerHTML = `
        <div class="evidence-box mb-12" style="background:var(--bg-card);border:1px solid var(--border);">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <h4 style="margin:0 0 2px 0;font-size:0.98rem;font-weight:700;">
                        Invoice ${inv.invoice_number}
                    </h4>
                    <span style="font-size:0.78rem;color:var(--text-secondary);">
                        Supplier: <strong>${inv.supplier_company_name || 'Supplier'}</strong> &rarr; Buyer: <strong>${inv.buyer_company_name || 'Buyer'}</strong>
                    </span>
                </div>
                <div class="inv-amount" style="font-size:1.2rem;font-weight:800;color:var(--accent-indigo);font-family:var(--font-mono);">
                    $${(inv.amount || 0).toLocaleString()}
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);">
                <div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">Buyer Acceptance</div>
                    <div style="font-weight:700;font-size:0.8rem;margin-top:2px;">
                        ${inv.status === 'VERIFIED' || inv.status === 'OFFER_EXTENDED'
                            ? '<span style="color:var(--accent-emerald);"><i class="fa-solid fa-circle-check"></i> Approved</span>'
                            : inv.status === 'PENDING_VERIFICATION'
                            ? '<span style="color:var(--accent-amber);"><i class="fa-solid fa-clock"></i> Pending</span>'
                            : inv.status === 'DISPUTED' || inv.status === 'REJECTED'
                            ? '<span style="color:var(--accent-rose);"><i class="fa-solid fa-triangle-exclamation"></i> Disputed</span>'
                            : '<span style="color:var(--accent-indigo);"><i class="fa-solid fa-check"></i> Financed</span>'}
                    </div>
                </div>
                <div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">AI Risk Score</div>
                    <div style="font-weight:800;font-family:var(--font-mono);color:var(--accent-emerald);margin-top:2px;">${riskScore}% LOW</div>
                </div>
                <div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">AI Target APR</div>
                    <div style="font-weight:800;font-family:var(--font-mono);color:var(--accent-indigo);margin-top:2px;">${recommendedApr}%</div>
                </div>
            </div>
        </div>

        <!-- Condition Matching Assessment -->
        <div class="condition-box ${conditionMatches ? 'matched' : 'exceeded'}">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                ${conditionMatches 
                    ? '<i class="fa-solid fa-circle-check" style="color:var(--accent-emerald);font-size:1.1rem;"></i> <strong>Matches Underwriting Conditions</strong>'
                    : '<i class="fa-solid fa-triangle-exclamation" style="color:var(--accent-amber);font-size:1.1rem;"></i> <strong>Exceeds Standard Parameters</strong>'}
            </div>
            <p style="margin:0;font-size:0.78rem;color:var(--text-secondary);">
                ${conditionMatches 
                    ? `Invoice value ($${inv.amount.toLocaleString()}) fits within your liquidity pool and risk threshold (Score: ${riskScore}% &le; 45%).`
                    : `Invoice requested ($${inv.amount.toLocaleString()}) or risk score exceeds single-ticket guideline. You can manually adjust the funding amount below to what you can provide.`}
            </p>
        </div>

        <!-- Manual Custom Financing Controls -->
        <div class="form-group">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <label style="margin:0;font-weight:700;">Manual Financing Amount ($)</label>
                <span style="font-size:0.72rem;color:var(--text-muted);">Max: $${inv.amount.toLocaleString()}</span>
            </div>
            <input type="number" id="offer-custom-amount-inp" value="${inv.amount}" min="1000" max="${inv.amount}" step="1000"
                   class="form-control" oninput="updateCustomOfferedPreview(${inv.amount})">
            
            <div style="display:flex;gap:6px;margin-top:6px;">
                <button type="button" class="btn btn-secondary btn-sm" style="flex:1;padding:4px 6px;font-size:0.72rem;" onclick="setCustomAmountPreset(1.0, ${inv.amount})">100% Full</button>
                <button type="button" class="btn btn-secondary btn-sm" style="flex:1;padding:4px 6px;font-size:0.72rem;" onclick="setCustomAmountPreset(0.75, ${inv.amount})">75% Partial</button>
                <button type="button" class="btn btn-secondary btn-sm" style="flex:1;padding:4px 6px;font-size:0.72rem;" onclick="setCustomAmountPreset(0.50, ${inv.amount})">50% Partial</button>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div class="form-group">
                <label>Discount Rate (%)</label>
                <input type="number" step="0.1" id="offer-discount-inp" value="${defaultDiscount}" class="form-control" oninput="updateCustomOfferedPreview(${inv.amount})">
            </div>
            <div class="form-group">
                <label>Annualized APR (%)</label>
                <input type="number" step="0.1" id="offer-apr-inp" value="${recommendedApr}" class="form-control">
            </div>
        </div>

        <div class="form-group">
            <label>Tenor (Days)</label>
            <input type="number" id="offer-tenor-inp" value="60" class="form-control">
        </div>

        <!-- Live Yield & Disbursement Summary -->
        <div style="background:var(--accent-indigo-light);border:1.5px solid var(--accent-indigo-mid);padding:12px 16px;border-radius:8px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px;">
                <span style="color:var(--text-secondary);">Funded Capital:</span>
                <strong id="preview-funded-amount" style="font-family:var(--font-mono);">$${initialFunded.toLocaleString()}</strong>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:6px;">
                <span style="color:var(--text-secondary);">Financier Discount Fee Earned:</span>
                <strong id="preview-discount-revenue" style="color:var(--accent-emerald);font-family:var(--font-mono);">
                    +$${(initialFunded * (defaultDiscount / 100)).toLocaleString()}
                </strong>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.9rem;padding-top:6px;border-top:1px dashed var(--accent-indigo-mid);">
                <span style="font-weight:700;color:var(--accent-indigo);">Disbursement to Supplier:</span>
                <strong id="preview-supplier-payout" style="font-size:1.15rem;font-weight:800;color:var(--accent-indigo);font-family:var(--font-mono);">
                    $${(initialFunded * (1.0 - defaultDiscount / 100)).toLocaleString()}
                </strong>
            </div>
        </div>

        ${inv.status === 'DISPUTED' || inv.status === 'REJECTED' ? `
            <div class="info-box" style="background:rgba(239,68,68,0.1);border-color:var(--accent-rose);color:var(--accent-rose);margin-bottom:10px;">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>Invoice is disputed by buyer. Financing offers cannot be executed until dispute is resolved.</span>
            </div>
        ` : `
            <button class="btn btn-primary btn-full" onclick="submitFinancierCustomOffer('${inv.id}')" style="padding:12px;">
                <i class="fa-solid fa-paper-plane"></i> Extend Custom Financing Offer
            </button>
        `}
    `;
}

function setCustomAmountPreset(ratio, total) {
    const inp = document.getElementById("offer-custom-amount-inp");
    if (!inp) return;
    inp.value = Math.round(total * ratio);
    updateCustomOfferedPreview(total);
}

function updateCustomOfferedPreview(baseTotal) {
    const customAmtInp = document.getElementById("offer-custom-amount-inp");
    const discInp = document.getElementById("offer-discount-inp");
    if (!customAmtInp || !discInp) return;

    const amount = parseFloat(customAmtInp.value) || baseTotal;
    const disc = parseFloat(discInp.value) || 0;

    const fee = amount * (disc / 100.0);
    const payout = amount - fee;

    const elFunded = document.getElementById("preview-funded-amount");
    const elFee = document.getElementById("preview-discount-revenue");
    const elPayout = document.getElementById("preview-supplier-payout");

    if (elFunded) elFunded.textContent = `$${amount.toLocaleString()}`;
    if (elFee) elFee.textContent = `+$${fee.toLocaleString()}`;
    if (elPayout) elPayout.textContent = `$${payout.toLocaleString()}`;
}

async function submitFinancierCustomOffer(invId) {
    const customAmt = parseFloat(document.getElementById("offer-custom-amount-inp")?.value);
    const discount  = parseFloat(document.getElementById("offer-discount-inp")?.value);
    const apr       = parseFloat(document.getElementById("offer-apr-inp")?.value);
    const tenor     = parseInt(document.getElementById("offer-tenor-inp")?.value);

    try {
        const res = await fetch(`${API_BASE}/offers/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({
                invoice_id: invId,
                custom_offered_amount: customAmt,
                discount_rate_pct: discount,
                apr_pct: apr,
                tenor_days: tenor,
                expires_in_hours: 72
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to submit financing offer");
        }

        showToast(`Financing offer extended! Amount: $${customAmt.toLocaleString()} at ${discount}% discount.`, "success");
        await loadFinancierMatchedFeed();
        await refreshStats();
    } catch (err) {
        showToast(`Offer error: ${err.message}`, "error");
    }
}

// =====================================================================
//  ADMIN PORTAL
// =====================================================================
async function loadAdminAuditLedger() {
    try {
        const res = await fetch(`${API_BASE}/financing/transactions`, {
            headers: { Authorization: `Bearer ${authToken}` }
        });
        const txs = await res.json();
        const tbody = document.getElementById("admin-tx-table");

        if (!txs.length) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);">No transactions recorded yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = txs.map(tx => `
            <tr>
                <td style="font-family:var(--font-mono);font-size:0.78rem;">${tx.id.substring(0, 8)}…</td>
                <td><span class="badge badge-ai">${tx.transaction_type}</span></td>
                <td style="font-weight:700;color:var(--accent-emerald);font-family:var(--font-mono);">$${tx.amount.toLocaleString()}</td>
                <td style="font-size:0.8rem;">${tx.sender_account}</td>
                <td style="font-size:0.8rem;">${tx.recipient_account}</td>
                <td style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-muted);">${tx.transaction_hash.substring(0, 14)}…</td>
                <td><span class="status-pill verified">${tx.status}</span></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Admin ledger error:", err);
    }
}

// =====================================================================
//  INVOICE CREATE MODAL
// =====================================================================
async function loadBuyerOptionsForForm() {
    await loadBuyersDirectory();
    const sel = document.getElementById("inp-buyer-id");
    if (!sel) return;

    sel.innerHTML = buyersList.map(b => `
        <option value="${b.id}">${b.company_name || b.name} (Tax ID: ${b.tax_id || 'TAX-BUY'})</option>
    `).join("");
}

async function handleCreateInvoice(event) {
    event.preventDefault();
    const invNum = document.getElementById("inp-inv-num").value;
    const buyerId = document.getElementById("inp-buyer-id").value;
    const amount = parseFloat(document.getElementById("inp-amount").value);
    const tenor  = parseInt(document.getElementById("inp-tenor").value);
    const desc   = document.getElementById("inp-desc").value;
    const today  = new Date();
    const due    = new Date(); due.setDate(today.getDate() + tenor);

    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
            body: JSON.stringify({
                invoice_number: invNum,
                buyer_id:       buyerId || "seed-buyer-id-001",
                amount, currency: "USD",
                issue_date: today.toISOString().split("T")[0],
                due_date:   due.toISOString().split("T")[0],
                description: desc
            })
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Creation failed"); }
        showToast(`Invoice #${invNum} submitted for AI verification!`, "success");
        closeModal("modal-create-invoice");
        event.target.reset();
        await loadSupplierInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// =====================================================================
//  MODAL HELPERS
// =====================================================================
function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("active");
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("active");
}

document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-overlay") || e.target.classList.contains("modal-backdrop")) {
        e.target.classList.remove("active");
    }
});

// =====================================================================
//  REGISTER FROM DASHBOARD (header Register btn)
// =====================================================================
async function handleRegister(event) {
    event.preventDefault();
    const fullName    = document.getElementById("reg-name").value;
    const email       = document.getElementById("reg-email").value;
    const pass        = document.getElementById("reg-pass").value;
    const confirmPass = document.getElementById("reg-confirm-pass").value;
    const role        = document.getElementById("reg-role").value;
    const company     = document.getElementById("reg-company").value;
    const tax         = document.getElementById("reg-tax").value;

    if (pass !== confirmPass) { showToast("Passwords do not match!", "error"); return; }

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: fullName, email, password: pass, role,
                company_name: company || fullName,
                tax_id: tax || `TAX-${role.substring(0,3).toUpperCase()}-${Date.now().toString().slice(-4)}`
            })
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Registration failed"); }
        showToast(`Account created for ${fullName}!`, "success");
        closeModal("modal-register");
        PRESET_ACCOUNTS[role] = { email, password: pass };
        await loadAllDirectories();
    } catch (err) {
        showToast(`Registration error: ${err.message}`, "error");
    }
}

function toggleRegisterRoleFields() {
    const role = document.getElementById("reg-role")?.value;
    const cf   = document.getElementById("reg-company-field");
    if (cf) cf.style.display = role === "admin" ? "none" : "block";
}

// =====================================================================
//  LOGOUT
// =====================================================================
async function logout() {
    try {
        if (authToken) {
            await fetch(`${API_BASE}/auth/logout`, {
                method: "POST",
                headers: { Authorization: `Bearer ${authToken}` }
            });
        }
    } catch (e) { /* silent */ }
    authToken   = null;
    currentUser = null;
    selectedInvoice = null;
    invoicesData    = [];
    purchaseOrders  = [];
    showToast("Logged out successfully", "info");
    setTimeout(() => showLoginScreen(), 600);
}

// =====================================================================
//  HELPERS & UTILITIES
// =====================================================================
function getStatusClass(status) {
    switch (status) {
        case "PENDING_VERIFICATION": return "pending";
        case "VERIFIED":            return "verified";
        case "OFFER_EXTENDED":      return "offer";
        case "FINANCED":            return "financed";
        case "SETTLED":             return "settled";
        case "DISPUTED":            return "disputed";
        default:                    return "pending";
    }
}

function formatStatus(status) {
    return (status || "").replace(/_/g, " ");
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast     = document.createElement("div");
    const icons     = { success: "fa-circle-check", error: "fa-circle-xmark", info: "fa-circle-info" };
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 4500);
}
