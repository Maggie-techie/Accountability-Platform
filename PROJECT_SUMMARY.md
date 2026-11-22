# Nyeri County Accountability Platform — Project Summary

*A plain-language walkthrough of what this platform does, why it exists, and how it works — from the problem it solves to how administrators keep it running.*

---

## 🎯 The Problem We're Solving

**In simple terms:** Nyeri County residents (and Kenyans in general) have a hard time finding out how their tax money is actually spent. Government budgets, constituency development funds (NG-CDF), and audit reports exist, but they're scattered across different websites, published as hard-to-read PDFs, and written in technical language that only accountants understand.

**The result:** Citizens can't easily answer basic questions like:
- "How much money did my constituency get this year?"
- "Did the Auditor-General find any problems with how it was spent?"
- "Is my MP or Governor doing a good job managing public funds?"

**What this platform does:** It pulls all that scattered public data into one place, organizes it by leader and location, uses AI to spot unusual patterns, and explains everything in plain English — so any resident, journalist, or oversight body can follow the money without needing a finance degree.

---

## 📊 Where the Data Comes From

All data on this platform comes from **official public sources** — nothing is secret or leaked. We collect and organize what's already published by:

| Source | What It Contains | How Often Updated |
|--------|------------------|-------------------|
| **Office of the Auditor-General (OAG)** | Audit reports on county departments, constituencies, and state entities — including findings of misappropriation, irregular spending, and clean opinions | Annually (when reports are tabled in Parliament/County Assembly) |
| **National Treasury / NG-CDF Board** | Disbursement records showing how much each constituency received, for which projects, in each financial year | Quarterly/Annually |
| **Nyeri County Fiscal Reports** | County revenue (equitable share, own-source revenue, conditional grants) and expenditure (development vs. recurrent) by department | Annually (budget) + Quarterly (implementation) |
| **County Assembly / Parliamentary Records** | Leadership info — who is the Governor, who are the 6 MPs, their parties, tenures | After elections (every 5 years) |

**Important:** Every number on this platform links back to its original document. We don't create data — we make existing data findable and understandable.

---

## 🏗️ How the Platform Is Organized

Think of it as a **digital filing cabinet** with four main drawers:

### 1. Leaders Directory (`/leaders`)
**The "Who's Who" of Nyeri governance.**
- **Governor** — County chief executive, accountable for the full county budget (~KSh 7.8B)
- **6 Members of Parliament** — Each oversees their constituency's NG-CDF allocation (~KSh 100–150M/year each)
- **Accountability Score** — A 0–100 rating for each leader based on audit findings, budget absorption, and Auditor-General opinions (explained below)
- **Search & Filter** — Find any leader by name, constituency, or position instantly

### 2. County Dashboard (`/county`)
**The big picture — Nyeri County Government finances.**
- **Revenue breakdown** — Equitable share (national government), conditional grants (earmarked), own-source revenue (local taxes/fees)
- **Spending trends** — Development (building things) vs. Recurrent (salaries, operations) over multiple years
- **Department performance** — Which departments spent their budgets well (absorption rate %) and which didn't
- **Audit findings** — All OAG findings for county departments in one list

### 3. Constituency Profiles (`/constituencies/[name]`)
**Deep dive into each of the 6 constituencies:**
- **Kieni, Mathira, Othaya, Tetu, Mukurwe-ini, Nyeri Town**
- **MP profile** — Name, party, contact info, photo
- **NG-CDF allocation history** — Year-by-year breakdown of funds received
- **Project-level data** — What the money was meant for (bursaries, classrooms, water, etc.)
- **Audit findings specific to that constituency** — Misappropriation vs. correct appropriation
- **AI anomaly detection** — Unusual patterns flagged automatically (see AI section below)
- **Downloadable PDF report** — One-click accountability report for that constituency

### 4. AI Assistant (`/assistant`)
**Ask questions in plain English, get answers grounded in real data.**
- "Who is the MP for Kieni?" → Instant answer from database
- "What's Nyeri County's budget breakdown?" → Real numbers from latest fiscal year
- "Audit findings for Mathira" → Actual OAG findings
- "Explain Kieni's accountability score" → AI analysis of why the score is what it is
- **Only answers from verified platform data** — no hallucinations, no opinions

---

## 🤖 The AI Layer — What It Does (and Doesn't Do)

### What It Does
1. **Pattern Detection (GNN Model)** — A Graph Neural Network looks at how entities (constituencies, departments, years) connect to each other. It learns "normal" patterns and flags nodes that behave unusually — like a constituency with 5x more audit findings than peers in the same year.

2. **Plain-Language Explanations** — Every anomaly gets a human-readable reason: *"Kieni FY2023/24: Unusually high allocation (KSh 842M); Multiple misappropriation findings (3)."*

3. **Fiscal Health Narratives** — AI summarizes county financial health, department absorption trends, and risk levels in narrative form.

4. **Question Answering** — Routes your question to the right data endpoint, fetches real numbers, and formats the answer.

### What It Doesn't Do
- ❌ Make up numbers or "hallucinate" facts
- ❌ Access private or non-public data
- ❌ Pass judgment on guilt/innocence — it only flags patterns for human investigation
- ❌ Replace the Auditor-General or other oversight bodies

### The Three Detection Methods (Ensemble Approach)
The system doesn't rely on just one AI technique — it combines three, so a finding has to be unusual in multiple ways to be flagged:

| Method | What It Catches | Weight |
|--------|-----------------|--------|
| **Embedding Distance** | Entities far from their peers in the learned "normal behavior" map | 40% |
| **Isolation Forest** | Statistical outliers that are easy to separate from the pack | 30% |
| **Graph Reconstruction Error** | Connections the model fails to predict (unexpected relationships) | 30% |

**Result:** More reliable flags, fewer false alarms.

---

## 📈 The Accountability Score — How It's Calculated

Every leader (Governor + 6 MPs) gets a **0–100 score**. Higher = better accountability track record.

### For Constituencies/MPs (3 Factors)

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| **Allocation Utilization** | 30% | Ratio of "correct appropriation" findings to total findings — are funds used as intended? |
| **Audit Findings Severity** | 40% | Misappropriation count + amount at risk — how serious are the problems? |
| **OAG Opinion & Audit Status** | 30% | Auditor-General's opinion (Unqualified=clean, Qualified/Adverse=problems) + audit status |

### For Governor (2 Factors)

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| **Department Absorption** | 60% | Average % of budget actually spent across all county departments — low absorption = unimplemented projects |
| **Audit Penalty** | 40% | Total misappropriated amount as % of total revenue — capped so one huge finding doesn't zero the score |

**Scores are recalculated automatically** whenever new data is uploaded. They're not opinions — they're math based on official records.

---

## 🛠️ Admin Panel — How the Site Is Managed

The admin panel (`/admin`) is a **separate, password-protected area** for platform maintainers. It's not visible to the public.

### What Admins Can Do

#### 1. Dashboard Overview
- System health at a glance
- Record counts for each data type
- Last update timestamps
- Quick links to common tasks

#### 2. Data Management (`/admin/leaders`, `/admin/constituencies`, etc.)
**CRUD interface for every data collection:**
- **View** — Paginated, searchable tables of all records
- **Add** — Form to create new records (with validation)
- **Edit** — Click any row to modify
- **Delete** — With confirmation
- **Bulk operations** — Select multiple, delete/archive

**Collections managed:**
- Leaders (Governor, MPs)
- Constituencies
- County Financial Data
- NG-CDF Allocations
- Audit Findings (County + Constituency)
- Department Absorption Data

#### 3. Dataset Upload (`/admin/upload`)
**For large updates — CSV/Excel import instead of one-by-one:**
- Drag-and-drop or file picker
- Column mapping (match your spreadsheet columns to database fields)
- Preview before import
- Validation report (rows with errors highlighted)
- Rollback if something goes wrong

**Typical use case:** New Auditor-General report comes out → export findings to CSV → upload → all 6 constituency profiles updated in minutes.

#### 4. Data Validation (`/admin/validation`)
**Quality checks before data goes live:**
- Schema validation (required fields, correct types)
- Cross-reference checks (e.g., every allocation references a valid constituency)
- Duplicate detection
- Anomaly scan (amounts that are 10x normal range)
- **Only validated data gets published** — staging area approach

#### 5. AI Model Management (`/admin/model`)
**Control the GNN anomaly detector:**
- **Train model** — One-click retraining on latest data (takes 30–60 seconds)
- **Model status** — Is it trained? When? How many nodes/edges? Validation AUC?
- **Download model** — Backup the trained weights
- **Force retrain** — After major data upload

#### 6. System Management (`/admin/system`)
- **Cache management** — Clear API cache, view hit/miss stats
- **Log viewer** — Recent errors, slow queries, upload history
- **Settings** — API keys, feature toggles, maintenance mode

---

## 🔄 The Data Lifecycle — From Source to Screen

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OFFICIAL       │     │  ADMIN UPLOADS   │     │  PLATFORM       │
│  SOURCES        │────▶│  (CSV/Excel or   │────▶│  DATABASE       │
│  (PDFs, Reports)│     │   manual entry)  │     │  (MongoDB)      │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  API LAYER      │
                    │  (Flask + Cache)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │  FRONTEND│  │  AI      │  │  EXPORTS │
       │  (React) │  │  ENGINE  │  │  (PDF)   │
       └──────────┘  └──────────┘  └──────────┘
```

**Step by step:**

1. **Source documents published** — OAG tables report, Treasury releases disbursement data, County publishes budget
2. **Admin collects & formats** — Downloads PDFs, extracts tables into structured CSV/Excel
3. **Upload via admin panel** — Drag-and-drop, column mapping, validation preview
4. **Validation runs** — Checks for errors, duplicates, cross-reference integrity
5. **Data lands in MongoDB** — Structured, queryable, versioned
6. **API serves it** — REST endpoints with 5–10 minute caching, ETag support
7. **Frontend displays it** — Progressive loading, skeletons, instant interactions
8. **AI analyzes it** — GNN retrains on schedule or on-demand, detects anomalies
9. **User consumes it** — Browses dashboards, asks AI, downloads PDF reports

---

## 🔒 Security & Privacy

| Aspect | Approach |
|--------|----------|
| **Authentication** | Admin panel: username/password (bcrypt hashed). Public pages: no login required. |
| **Authorization** | Role-based — only admins access `/admin/*`. API endpoints public (read-only). |
| **Data sensitivity** | **Zero private data** — everything is already public record. No PII beyond what's in official gazettes. |
| **Transport** | HTTPS in production (enforced via reverse proxy) |
| **Caching** | In-memory with TTL — no persistent cache of sensitive queries |
| **AI safety** | Model only sees aggregated, anonymized features — no raw names in embeddings |

---

## 📦 Technical Stack (For Context)

| Layer | Technology | Why |
|-------|------------|-----|
| **Frontend** | React 18 + Vite + Tailwind CSS | Fast, modern, small bundle |
| **Routing** | React Router v6 | Code-splitting (lazy load AI page) |
| **Charts** | Recharts | Declarative, responsive |
| **Backend** | Flask (Python) | Simple, flexible, great ML ecosystem |
| **Database** | MongoDB | Flexible schema for varied govt data |
| **AI/ML** | PyTorch Geometric (GNN) + scikit-learn | Graph neural nets + ensemble detectors |
| **Caching** | In-memory + ETag/304 | Sub-millisecond repeat requests |
| **PDF Reports** | ReportLab / WeasyPrint | Server-side generation |

---

## 🚀 Future Enhancements (Roadmap)

| Priority | Feature | Why |
|----------|---------|-----|
| **High** | Project-level tracking | Drill from constituency → specific school/clinic/water project |
| **High** | Vendor/contractor network | See which companies win tenders across constituencies |
| **Medium** | Benford's Law digit analysis | Mathematical fraud detection on payment amounts |
| **Medium** | SMS/USSD interface | Reach citizens without smartphones |
| **Medium** | Multi-county support | Template for other 46 counties |
| **Low** | Predictive risk scoring | Forecast which projects might stall next year |
| **Low** | Public API for researchers | Let others build on the data |

---

## 🤝 How to Contribute / Extend

This is an **open civic-tech project**. You can help by:

1. **Reporting data gaps** — "Constituency X missing FY2023 allocations"
2. **Improving parsers** — Better PDF-to-CSV extraction for OAG reports
3. **Translating UI** — Kiswahili, Kikuyu versions
4. **Adding visualizations** — New chart types, comparison views
5. **Auditing the AI** — Review flagged anomalies, improve explanations

**All data sources are cited.** If you spot an error, trace it to the source document — that's the ultimate truth.

---

## 📞 Questions?

This platform was built as a **final-year civic technology project** with the goal of making Nyeri County's public financial records easier to find, understand, and investigate.

**It is not affiliated with the Nyeri County Government or any political party.**

Every figure links back to its original document. Data indicators require independent verification before being used for formal accountability actions.

---

*Last updated: November 2026*