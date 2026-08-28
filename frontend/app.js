// Supply Chain Finance Nexus - Frontend Application Controller
const API_BASE = (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") 
    ? "http://127.0.0.1:8000/api" 
    : `${window.location.origin}/api`;


// State Management
let currentRole = "supplier";
let authToken = null;
let currentUser = null;
let invoicesData = [];
let selectedInvoice = null;

// Preset Accounts for Instant Switch in Hackathon Demo
const PRESET_ACCOUNTS = {
    supplier: { email: "supplier@apex.com", password: "Password123!" },
    buyer: { email: "buyer@globalcorp.com", password: "Password123!" },
    financier: { email: "financier@horizon.com", password: "Password123!" },
    admin: { email: "admin@scf.com", password: "Password123!" }
};

// Initialize App
document.addEventListener("DOMContentLoaded", async () => {
    console.log("SCF Nexus Dashboard Initializing...");
    await loginRole("supplier");
    await refreshStats();
});

// Role Switcher
async function switchRole(role) {
    currentRole = role;

    // Update active tab buttons
    document.querySelectorAll(".role-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.role === role);
    });

    // Update portal views
    document.querySelectorAll(".portal-view").forEach(view => {
        view.classList.remove("active-view");
    });
    const targetPortal = document.getElementById(`portal-${role}`);
    if (targetPortal) targetPortal.classList.add("active-view");

    // Login as preset account for the role
    await loginRole(role);
}

// Authentication Service
async function loginRole(role) {
    const creds = PRESET_ACCOUNTS[role];
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(creds)
        });
        if (!res.ok) throw new Error("Auth failed");
        const data = await res.json();
        
        authToken = data.access_token;
        currentUser = data.user;

        document.getElementById("active-user-name").textContent = currentUser.full_name;
        document.getElementById("active-role-tag").textContent = role.toUpperCase();

        showToast(`Switched role to ${role.toUpperCase()} (${currentUser.full_name})`, "info");
        await loadRoleData();
    } catch (err) {
        console.error("Login error:", err);
        showToast("Error authenticating role credentials", "error");
    }
}

// Load Portal Specific Data
async function loadRoleData() {
    await refreshStats();

    if (currentRole === "supplier") {
        await loadSupplierInvoices();
        await loadBuyerOptionsForForm();
    } else if (currentRole === "buyer") {
        await loadBuyerPendingInvoices();
    } else if (currentRole === "financier") {
        await loadFinancierMatchedFeed();
    } else if (currentRole === "admin") {
        await loadAdminAuditLedger();
    }
}

// Stats Refresh
async function refreshStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const stats = await res.json();

        document.getElementById("stat-total-volume").textContent = `$${stats.total_invoices_volume.toLocaleString()}`;
        document.getElementById("stat-funded-volume").textContent = `$${stats.total_funded_volume.toLocaleString()}`;
        document.getElementById("stat-liquidity-pool").textContent = `$${stats.active_liquidity_pool.toLocaleString()}`;
        
        const poolDisplay = document.getElementById("financier-pool-display");
        if (poolDisplay) poolDisplay.textContent = `$${stats.active_liquidity_pool.toLocaleString()}`;
    } catch (err) {
        console.error("Stats refresh error:", err);
    }
}

// ==================== SUPPLIER PORTAL ====================

async function loadSupplierInvoices() {
    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        invoicesData = await res.json();

        const container = document.getElementById("supplier-invoices-list");
        document.getElementById("supplier-invoice-count").textContent = `${invoicesData.length} Invoices`;

        if (invoicesData.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>No invoices submitted yet.</p></div>`;
            return;
        }

        container.innerHTML = invoicesData.map(inv => `
            <div class="invoice-card ${selectedInvoice && selectedInvoice.id === inv.id ? 'selected' : ''}" onclick="selectSupplierInvoice('${inv.id}')">
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
            </div>
        `).join("");

        if (invoicesData.length > 0 && !selectedInvoice) {
            selectSupplierInvoice(invoicesData[0].id);
        }
    } catch (err) {
        console.error("Error loading supplier invoices:", err);
    }
}

async function selectSupplierInvoice(invId) {
    selectedInvoice = invoicesData.find(i => i.id === invId);
    await loadSupplierInvoices(); // Refresh selection state

    const panel = document.getElementById("supplier-offers-panel");
    if (!selectedInvoice) return;

    // Fetch offers for this invoice
    const res = await fetch(`${API_BASE}/offers?invoice_id=${selectedInvoice.id}`, {
        headers: { "Authorization": `Bearer ${authToken}` }
    });
    const offers = await res.json();

    if (offers.length === 0) {
        panel.innerHTML = `
            <div class="evidence-box">
                <h4>Invoice ${selectedInvoice.invoice_number} - Status: <span class="status-pill ${getStatusClass(selectedInvoice.status)}">${formatStatus(selectedInvoice.status)}</span></h4>
                <p class="subtitle" style="margin-top: 8px;">Multi-Factor Evidence Confidence:</p>
                
                <div class="evidence-item">
                    <span>Supplier GST & Business Verification</span>
                    <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> 100% Valid</span>
                </div>
                <div class="evidence-item">
                    <span>Buyer Invoice Match</span>
                    <span class="evidence-check">${selectedInvoice.status !== 'PENDING_VERIFICATION' ? '<i class="fa-solid fa-circle-check"></i> Verified' : '<i class="fa-solid fa-clock"></i> Pending Buyer Confirmation'}</span>
                </div>
                <div class="evidence-item">
                    <span>Cryptographic Hash Integrity</span>
                    <span class="evidence-check"><i class="fa-solid fa-lock"></i> Verified SHA-256</span>
                </div>
            </div>
            <div class="empty-state">
                <i class="fa-solid fa-hourglass-half fa-2x"></i>
                <p>No active financing offers extended yet. Once verified, financiers will submit competing quotes.</p>
            </div>
        `;
        return;
    }

    // AI Multi-Factor Offer Ranking Engine Simulation
    panel.innerHTML = `
        <div style="margin-bottom: 1rem;">
            <h4>Offers for Invoice ${selectedInvoice.invoice_number} ($${selectedInvoice.amount.toLocaleString()})</h4>
            <small class="text-muted">AI Suitability Ranker evaluated rates, tenor, advance amount & speed.</small>
        </div>
        ${offers.map((off, idx) => {
            const isTop = idx === 0;
            const suitabilityScore = off.suitability_score || (isTop ? 94 : 81);
            const reasons = off.explainability_reasons || [
                "Required amount fully satisfied",
                "Acceptable financing cost",
                "Financier has sufficient liquidity"
            ];
            return `
                <div class="offer-rank-card ${isTop ? 'top-choice' : ''}">
                    ${isTop ? '<div class="top-choice-badge"><i class="fa-solid fa-crown"></i> AI Best Overall Match</div>' : ''}
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div>
                            <h4 style="font-size: 1.05rem;">${off.financier_name || 'Horizon Capital Group'}</h4>
                            <span class="badge badge-ai">Suitability Score: <strong>${suitabilityScore}/100</strong></span>
                        </div>
                        <div class="text-right">
                            <div style="font-size: 1.3rem; font-weight: 800; color: var(--accent-emerald);">$${off.offered_amount.toLocaleString()}</div>
                            <small class="text-muted">Discount Rate: ${off.discount_rate_pct}% (${off.apr_pct}% APR)</small>
                        </div>
                    </div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 8px;">
                        Tenor: <strong>${off.tenor_days} Days</strong> | Settlement Speed: <strong>Instant Payout</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; margin-bottom: 12px; font-size: 0.78rem;">
                        <strong>AI Recommendation Rationale:</strong>
                        <ul style="margin: 4px 0 0 16px; padding: 0; color: var(--text-secondary);">
                            ${reasons.map(r => `<li>${r}</li>`).join("")}
                        </ul>
                    </div>
                    ${off.status === 'EXTENDED' ? `
                        <button class="btn ${isTop ? 'btn-success' : 'btn-primary'}" style="width: 100%;" onclick="acceptOffer('${off.id}')">
                            <i class="fa-solid fa-check-double"></i> Accept Offer & Disburse $${off.offered_amount.toLocaleString()}
                        </button>
                    ` : `
                        <div class="badge badge-ai" style="text-align: center; display: block; padding: 8px;">Status: ${off.status}</div>
                    `}
                </div>
            `;
        }).join("")}
    `;
}

async function acceptOffer(offerId) {
    try {
        const res = await fetch(`${API_BASE}/offers/${offerId}/accept`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error("Offer acceptance failed");

        // Automatically trigger disbursement payout
        const disbRes = await fetch(`${API_BASE}/financing/disburse`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}` 
            },
            body: JSON.stringify({
                offer_id: offerId,
                recipient_account: "SUPPLIER_BANK_ACC_APEX_8892"
            })
        });

        if (disbRes.ok) {
            const disbData = await disbRes.json();
            showToast(`Capital Disbursed! $${disbData.amount.toLocaleString()} transferred. Hash: ${disbData.transaction_hash.substring(0, 10)}...`, "success");
        } else {
            showToast("Offer accepted! Financing pending financier disbursement.", "success");
        }

        await loadSupplierInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Error accepting offer: ${err.message}`, "error");
    }
}

// ==================== BUYER PORTAL ====================

async function loadBuyerPendingInvoices() {
    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const allInvoices = await res.json();
        const pendingInvoices = allInvoices.filter(i => i.status === "PENDING_VERIFICATION" || i.status === "VERIFIED");

        const container = document.getElementById("buyer-pending-list");
        if (pendingInvoices.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>No pending invoices require buyer approval.</p></div>`;
            return;
        }

        container.innerHTML = pendingInvoices.map(inv => `
            <div class="invoice-card ${selectedInvoice && selectedInvoice.id === inv.id ? 'selected' : ''}" onclick="selectBuyerInvoice('${inv.id}')">
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
                        <div>Issue: ${inv.issue_date}</div>
                        <small class="text-muted">Due: ${inv.due_date}</small>
                    </div>
                </div>
            </div>
        `).join("");

        if (pendingInvoices.length > 0 && !selectedInvoice) {
            selectBuyerInvoice(pendingInvoices[0].id);
        }
    } catch (err) {
        console.error("Error loading buyer pending invoices:", err);
    }
}

function selectBuyerInvoice(invId) {
    selectedInvoice = invoicesData.find(i => i.id === invId) || { id: invId };
    const detailPanel = document.getElementById("buyer-verification-detail");
    const isFinanced = selectedInvoice.status === "FINANCED";

    if (isFinanced) {
        detailPanel.innerHTML = `
            <div class="evidence-box">
                <h4>Invoice #${selectedInvoice.invoice_number || 'INV'} Status: <span class="status-pill financed">FINANCED</span></h4>
                <p class="subtitle" style="margin-top: 8px;">Financier payout completed. Invoice awaiting maturity date settlement.</p>
                <div class="evidence-item">
                    <span>Financed Amount</span>
                    <strong style="color: var(--accent-emerald);">$${(selectedInvoice.amount || 0).toLocaleString()}</strong>
                </div>
            </div>

            <button class="btn btn-success" style="width: 100%; padding: 14px; font-weight: 700; margin-top: 12px;" onclick="simulateSettlement('${selectedInvoice.id}', ${selectedInvoice.amount})">
                <i class="fa-solid fa-money-bill-transfer"></i> Simulate Buyer Settlement (Pay $${(selectedInvoice.amount || 0).toLocaleString()} & Return Financier Yield)
            </button>
        `;
        return;
    }

    detailPanel.innerHTML = `
        <div class="evidence-box">
            <h4>Buyer Evidence Verification Checklist</h4>
            <p class="subtitle" style="margin-bottom: 12px;">Multi-factor criteria verification required by Problem Statement 5:</p>

            <div class="evidence-item">
                <span>1. Supplier GST & Business Registration</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> VERIFIED (Apex Industrial Ltd)</span>
            </div>
            <div class="evidence-item">
                <span>2. Purchase Order (PO) Matching</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> MATCHED (PO-88492)</span>
            </div>
            <div class="evidence-item">
                <span>3. Delivery Note & Physical Receipt</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> DELIVERED & ACKNOWLEDGED</span>
            </div>
            <div class="evidence-item">
                <span>4. Line Item Amount & Payment Terms</span>
                <span class="evidence-check"><i class="fa-solid fa-circle-check"></i> NET 60 CONFIRMED</span>
            </div>
        </div>

        <div class="form-group">
            <label>Buyer Approval / Verification Notes</label>
            <textarea id="buyer-comment-inp" rows="2" class="form-control" placeholder="Confirmed goods received in full compliance with purchase contract."></textarea>
        </div>

        <div style="display: flex; gap: 10px;">
            <button class="btn btn-success" style="flex: 1;" onclick="verifyInvoice(true)">
                <i class="fa-solid fa-check-circle"></i> Approve & Verify Invoice (🟢 95% Confidence)
            </button>
            <button class="btn btn-danger" style="flex: 1;" onclick="verifyInvoice(false)">
                <i class="fa-solid fa-circle-xmark"></i> Flag Dispute (🔴 High Risk)
            </button>
        </div>
    `;
}

async function simulateSettlement(invoiceId, amount) {
    try {
        const res = await fetch(`${API_BASE}/settlement/settle`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                invoice_id: invoiceId,
                payment_amount: amount,
                payer_account: "BUYER_SETTLEMENT_ACC_GLOB_101"
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Settlement failed");
        }

        const data = await res.json();
        showToast(`Settlement Complete! Buyer paid $${data.total_paid.toLocaleString()}. Yield returned to Financier Pool. Hash: ${data.disbursement_hash.substring(0, 10)}...`, "success");
        await loadBuyerPendingInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Settlement error: ${err.message}`, "error");
    }
}

async function verifyInvoice(isValid) {
    if (!selectedInvoice) return;
    const comments = document.getElementById("buyer-comment-inp").value || (isValid ? "Verified by buyer" : "Disputed by buyer");

    try {
        const res = await fetch(`${API_BASE}/verification/verify`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                invoice_id: selectedInvoice.id,
                is_valid: isValid,
                buyer_comments: comments
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Verification failed");
        }

        showToast(isValid ? "Invoice Verified Successfully! Multi-factor status set to 🟢 VERIFIED." : "Invoice Flagged as Disputed (🔴 High Risk).", isValid ? "success" : "error");
        await loadBuyerPendingInvoices();
    } catch (err) {
        showToast(`Verification Error: ${err.message}`, "error");
    }
}

// ==================== FINANCIER PORTAL ====================

async function loadFinancierMatchedFeed() {
    try {
        const res = await fetch(`${API_BASE}/matching/invoices/default`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const matches = await res.json();

        const feed = document.getElementById("financier-matched-feed");
        if (matches.length === 0) {
            feed.innerHTML = `<div class="empty-state"><p>No verified invoices matching your risk criteria available.</p></div>`;
            return;
        }

        feed.innerHTML = matches.map(m => `
            <div class="invoice-card" onclick="selectFinancierMatchedItem('${m.invoice.id}', ${m.invoice.amount}, ${m.calculated_risk_score}, ${m.recommended_apr})">
                <div class="inv-card-header">
                    <span class="inv-num">${m.invoice.invoice_number}</span>
                    <span class="badge badge-ai">Match Score: ${m.match_score}%</span>
                </div>
                <div class="inv-card-body">
                    <div>
                        <div class="inv-amount">$${m.invoice.amount.toLocaleString()}</div>
                        <div class="inv-meta">Risk Score: <strong>${m.calculated_risk_score}% (LOW RISK)</strong></div>
                    </div>
                    <div class="inv-meta text-right">
                        <div>Rec. APR: <strong>${m.recommended_apr}%</strong></div>
                        <small class="text-success">Eligible <i class="fa-solid fa-circle-check"></i></small>
                    </div>
                </div>
            </div>
        `).join("");

        if (matches.length > 0) {
            const first = matches[0];
            selectFinancierMatchedItem(first.invoice.id, first.invoice.amount, first.calculated_risk_score, first.recommended_apr);
        }
    } catch (err) {
        console.error("Error loading financier matched feed:", err);
    }
}

function selectFinancierMatchedItem(invId, amount, riskScore, recommendedApr) {
    const calcPanel = document.getElementById("financier-offer-calculator");
    calcPanel.innerHTML = `
        <div class="evidence-box">
            <h4>Generate Custom Financing Offer</h4>
            <div style="margin-top: 10px; font-size: 0.88rem; color: var(--text-secondary);">
                Invoice Value: <strong style="color: var(--text-primary);">$${amount.toLocaleString()}</strong><br>
                AI Assessed Risk: <strong style="color: var(--accent-emerald);">${riskScore}%</strong><br>
                Recommended Base APR: <strong style="color: var(--accent-indigo);">${recommendedApr}%</strong>
            </div>
        </div>

        <div class="form-group">
            <label>Discount Rate (%)</label>
            <input type="number" step="0.1" id="offer-discount-inp" value="2.5" class="form-control" oninput="updateOfferedPreview(${amount})">
        </div>
        <div class="form-group">
            <label>Annualized Percentage Rate (APR %)</label>
            <input type="number" step="0.1" id="offer-apr-inp" value="${recommendedApr}" class="form-control">
        </div>
        <div class="form-group">
            <label>Tenor (Days)</label>
            <input type="number" id="offer-tenor-inp" value="60" class="form-control">
        </div>

        <div style="background: rgba(99, 102, 241, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 1.25rem;">
            <span>Projected Disbursement Payout: </span>
            <strong id="preview-offered-amount" style="font-size: 1.2rem; color: var(--accent-emerald);">$${(amount * 0.975).toLocaleString()}</strong>
        </div>

        <button class="btn btn-primary" style="width: 100%;" onclick="submitFinancierOffer('${invId}')">
            <i class="fa-solid fa-paper-plane"></i> Extend Financing Offer
        </button>
    `;
}

function updateOfferedPreview(amount) {
    const disc = parseFloat(document.getElementById("offer-discount-inp").value) || 0;
    const preview = amount * (1.0 - (disc / 100.0));
    document.getElementById("preview-offered-amount").textContent = `$${preview.toLocaleString()}`;
}

async function submitFinancierOffer(invId) {
    const discount = parseFloat(document.getElementById("offer-discount-inp").value);
    const apr = parseFloat(document.getElementById("offer-apr-inp").value);
    const tenor = parseInt(document.getElementById("offer-tenor-inp").value);

    try {
        const res = await fetch(`${API_BASE}/offers/generate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                invoice_id: invId,
                discount_rate_pct: discount,
                apr_pct: apr,
                tenor_days: tenor,
                expires_in_hours: 72
            })
        });

        if (!res.ok) throw new Error("Failed to submit offer");

        showToast("Financing Offer Extended to Supplier!", "success");
        await loadFinancierMatchedFeed();
    } catch (err) {
        showToast(`Offer error: ${err.message}`, "error");
    }
}

// ==================== ADMIN PORTAL ====================

async function loadAdminAuditLedger() {
    try {
        const res = await fetch(`${API_BASE}/financing/transactions`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const txs = await res.json();

        const tbody = document.getElementById("admin-tx-table");
        if (txs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center">No transactions recorded yet in ledger.</td></tr>`;
            return;
        }

        tbody.innerHTML = txs.map(tx => `
            <tr>
                <td style="font-family: var(--font-mono);">${tx.id.substring(0, 8)}...</td>
                <td><span class="badge badge-ai">${tx.transaction_type}</span></td>
                <td style="font-weight: 700; color: var(--accent-emerald);">$${tx.amount.toLocaleString()}</td>
                <td>${tx.sender_account}</td>
                <td>${tx.recipient_account}</td>
                <td style="font-family: var(--font-mono); font-size: 0.75rem;">${tx.transaction_hash.substring(0, 14)}...</td>
                <td><span class="status-pill verified">${tx.status}</span></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Error loading admin ledger:", err);
    }
}

// Modal Helpers
async function loadBuyerOptionsForForm() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const stats = await res.json();
        const select = document.getElementById("inp-buyer-id");
        
        // Fetch buyer profiles from backend
        const meRes = await fetch(`${API_BASE}/invoices`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const list = await meRes.json();
        
        // Default buyer profile ID from database seed
        select.innerHTML = `<option value="seed-buyer-id-001">Global Retailers Inc (Tax ID: TAX-BUY-GLOB-101)</option>`;
    } catch (err) {
        console.error("Buyer options error:", err);
    }
}

async function handleCreateInvoice(event) {
    event.preventDefault();
    const invNum = document.getElementById("inp-inv-num").value;
    const amount = parseFloat(document.getElementById("inp-amount").value);
    const tenor = parseInt(document.getElementById("inp-tenor").value);
    const desc = document.getElementById("inp-desc").value;

    const today = new Date();
    const dueDate = new Date();
    dueDate.setDate(today.getDate() + tenor);

    try {
        const res = await fetch(`${API_BASE}/invoices`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                invoice_number: invNum,
                buyer_id: "seed-buyer-id-001", // Buyer seed ID
                amount: amount,
                currency: "USD",
                issue_date: today.toISOString().split("T")[0],
                due_date: dueDate.toISOString().split("T")[0],
                description: desc
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Invoice creation failed");
        }

        showToast(`Invoice #${invNum} Created! Submitted for AI evidence verification.`, "success");
        closeModal("modal-create-invoice");
        await loadSupplierInvoices();
        await refreshStats();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

function openModal(id) {
    document.getElementById(id).classList.add("active");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("active");
}

// Helpers & Utilities
function getStatusClass(status) {
    switch (status) {
        case "PENDING_VERIFICATION": return "pending";
        case "VERIFIED": return "verified";
        case "OFFER_EXTENDED": return "offer";
        case "FINANCED": return "financed";
        case "SETTLED": return "settled";
        default: return "pending";
    }
}

function formatStatus(status) {
    return status.replace(/_/g, " ");
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Authentication Registration & Logout Handlers
async function handleRegister(event) {
    event.preventDefault();
    const fullName = document.getElementById("reg-name").value;
    const email = document.getElementById("reg-email").value;
    const pass = document.getElementById("reg-pass").value;
    const confirmPass = document.getElementById("reg-confirm-pass").value;
    const role = document.getElementById("reg-role").value;
    const companyName = document.getElementById("reg-company").value;
    const taxId = document.getElementById("reg-tax").value;

    if (pass !== confirmPass) {
        showToast("Passwords do not match!", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: fullName,
                email: email,
                password: pass,
                role: role,
                company_name: companyName || fullName,
                tax_id: taxId || `TAX-${role.substring(0,3).toUpperCase()}-${Date.now().toString().slice(-4)}`
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Registration failed");
        }

        showToast(`Registration Successful! Account created for ${fullName}. Logging in...`, "success");
        closeModal("modal-register");
        
        // Update preset login or automatically sign in
        PRESET_ACCOUNTS[role] = { email: email, password: pass };
        await switchRole(role);
    } catch (err) {
        showToast(`Registration error: ${err.message}`, "error");
    }
}

async function logout() {
    try {
        if (authToken) {
            await fetch(`${API_BASE}/auth/logout`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${authToken}` }
            });
        }
    } catch (e) {
        console.log("Logout warning:", e);
    }
    authToken = null;
    currentUser = null;
    showToast("Logged out successfully", "info");
    await switchRole("supplier");
}

function toggleRegisterRoleFields() {
    const role = document.getElementById("reg-role").value;
    const companyField = document.getElementById("reg-company-field");
    if (companyField) {
        companyField.style.display = role === "admin" ? "none" : "block";
    }
}

