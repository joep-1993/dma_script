# PROJECT INDEX
_Project structure and technical specs. Update when: creating files, adding dependencies, defining schemas._

## Project Purpose
**Google Ads Campaign Automation**: Python script that processes Excel files to automatically update Google Ads Shopping campaigns with custom label 3 targeting (shop name inclusion/exclusion).

## Stack
**Primary**: Python 3.10+ script with Google Ads API | **Excel Processing**: openpyxl | **Automation**: Custom Label 3 listing tree rebuilding
**Optional Web UI**: FastAPI (Python 3.11) | Frontend: Bootstrap 5 + Vanilla JS | Database: PostgreSQL 15 | AI: OpenAI API | Deploy: Docker + docker-compose

## Directory Structure
```
dma-shop-campaigns/
├── cc1/                          # CC1 documentation
│   ├── TASKS.md                  # Task tracking
│   ├── LEARNINGS.md              # Knowledge capture
│   ├── BACKLOG.md                # Future planning
│   └── PROJECT_INDEX.md          # This file
├── campaign_processor.py         # ⭐ Main script - Google Ads campaign automation (with incremental saving & rate limiting)
├── google_ads_helpers.py         # Helper functions for listing tree operations
├── test_google_ads_init.py       # Test script for credentials verification
├── test_campaign_processor.py    # Test script for setup validation
├── test_improved_migration.py    # Test script for validating migration improvements (incremental saves, rate limiting)
├── check_adgroup_structure.py    # Diagnostic: Check ad group tree structure
├── test_exclusion_fix.py         # Diagnostic: Test exclusion logic on specific ad group
├── EXCLUSION_LOGIC_FIX_SUMMARY.md # Documentation: Exclusion logic fix details
├── toelichting.txt               # Requirements specification (Dutch)
├── changes.txt                   # Updated requirements from session
├── example_functions.txt         # Reference functions for listing trees
├── CAMPAIGN_PROCESSOR_README.md  # Main script documentation
├── PYCHARM_SETUP.md              # PyCharm setup guide
├── OS_DETECTION_INFO.md          # OS detection feature docs
├── backend/                      # (Optional web UI)
│   ├── main.py                   # FastAPI app with CORS
│   ├── database.py               # PostgreSQL connection
│   └── gpt_service.py            # AI integration
├── frontend/                     # (Optional web UI)
│   ├── index.html                # Main page (Bootstrap CDN)
│   ├── css/
│   │   └── style.css             # Custom styles
│   └── js/
│       └── app.js                # Vanilla JavaScript
├── docker-compose.yml            # Service orchestration
├── Dockerfile                    # Python container
├── requirements.txt              # Python dependencies (includes google-ads, openpyxl)
├── .env.example                  # Environment template (includes GOOGLE_ADS_* vars)
├── .env                          # Local environment (git ignored)
├── .gitignore                    # Version control excludes
├── README.md                     # Quick start guide
└── CLAUDE.md                     # Claude Code instructions
```

## Environment Variables

### Required for Campaign Processor
```bash
# Google Ads API Credentials (CRITICAL)
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=3011145605  # MCC account ID (used for bid strategy lookup)
```

### Optional (for web UI)
```bash
OPENAI_API_KEY=sk-...  # Your OpenAI API key
DATABASE_URL=postgresql://postgres:postgres@db:5432/myapp
AI_MODEL=gpt-4o-mini  # Or other OpenAI model
```

## Database Schema
```sql
-- Example table (modify as needed)
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Python Dependencies

### Core Dependencies
```
google-ads==24.1.0        # Google Ads API client library
openpyxl==3.1.2          # Excel file reading/writing
python-dotenv==1.0.0     # Environment variable management
```

### Optional (Web UI)
```
fastapi==0.104.1         # Web framework
uvicorn[standard]==0.24.0 # ASGI server
openai==1.35.0           # OpenAI API client
psycopg2-binary==2.9.9   # PostgreSQL driver
```

## Script Execution

### Main Script
```bash
python3 campaign_processor.py
```

**What it does**:
1. Loads Google Ads credentials from `.env`
2. Reads Excel file with two sheets: `toevoegen` (inclusion) and `uitsluiten` (exclusion)
3. **Inclusion logic** (processes rows with empty status in column G):
   - Reads columns A-G: shop_name, shop_id, maincat, maincat_id, custom_label_1, budget, status
   - Groups rows by unique (shop_name, maincat, custom_label_1) combinations
   - For each group:
     - Looks up bid strategy from MCC account (3011145605) based on custom_label_1
     - Creates campaign: `PLA/{maincat} {shop_name}_{custom_label_1}` with budget from Excel
     - Applies portfolio bid strategy from MCC (if found, else manual CPC)
     - Creates MULTIPLE ad groups (one per shop): `PLA/{shop_name}_{custom_label_1}`
     - Builds listing tree per ad group: maincat_id (CL4) → shop_name (CL3) with 1 cent bid
     - Enables concurrent processing of multiple shops in same campaign
   - Updates column G with TRUE/FALSE for all rows in group
4. **Exclusion logic** (processes rows with empty status in column F):
   - Finds existing campaigns by pattern
   - Rebuilds listing tree to exclude shop name (Custom Label 3)
   - **PRESERVES existing tree structures**: CL4 and CL1 subdivisions/units are maintained
   - Converts positive CL4 units to subdivisions when adding CL3 exclusions
   - Final structure: ROOT → CL1 → CL4 → CL3 (hierarchical, all existing targeting preserved)
   - Updates column F with TRUE/FALSE per row
   - **NEW**: Incremental saving every 50 campaigns (configurable via `save_interval` parameter)
   - **NEW**: Rate limiting with 0.5s delay between campaigns (configurable via `rate_limit_seconds` parameter)
   - **NEW**: Proper error propagation - only marks TRUE when fully successful
5. Saves results back to Excel file

**Key Features**:
- Auto-detects OS (Windows/WSL) and uses correct file paths
- Resumable processing: skips rows with existing status values
- Groups rows for efficient campaign creation (inclusion sheet)
- Hierarchical listing tree: maincat_id (CL4) → shop_name (CL3)
- Portfolio bid strategies from MCC account
- Budget per campaign from Excel
- Comprehensive error handling and progress reporting

**Configuration Constants**:
- Client Account ID: `3800751597`
- MCC Account ID: `3011145605` (for bid strategy lookup)
- Merchant Center ID: `140784594`
- Country: `NL` (Netherlands)
- Targeted product bid: `1 cent` (10,000 micros)
- Campaign label: `DMA_SCRIPT_JVS`
- Bid Strategy Mapping:
  - `a` → "DMA: Elektronica shops A - 0,25"
  - `b` → "DMA: Elektronica shops B - 0,21"
  - `c` → "DMA: Elektronica shops C - 0,17"

## API Endpoints (Optional Web UI)
- `GET /` - System status
- `GET /api/health` - Health check
- `POST /api/generate` - AI text generation
- `GET /static/*` - Frontend files

---
_Last updated: 2025-11-12_
