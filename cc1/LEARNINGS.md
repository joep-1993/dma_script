# LEARNINGS
_Capture mistakes, solutions, and patterns. Update when: errors occur, bugs are fixed, patterns emerge._

## Docker Commands
```bash
# Development
docker-compose up              # Run with logs
docker-compose up -d           # Run in background
docker-compose logs -f app     # View app logs
docker-compose down            # Stop everything
docker-compose down -v         # Stop and remove volumes

# Debugging
docker-compose ps              # Check status
docker exec -it <container> bash  # Enter container
```

## Common Issues & Solutions

### ModuleNotFoundError: No module named 'dotenv'
**Problem**: Script fails with missing dotenv module
**Solution**: Install dependencies with `pip install -r requirements.txt` or `pip3 install python-dotenv google-ads openpyxl`
**Root Cause**: Dependencies not installed before running script
_#claude-session:2025-11-11_

### Google Ads .env Variable Naming
**Problem**: Script can't find Google Ads credentials even though they're in .env
**Solution**: Variables must be prefixed with `GOOGLE_ADS_*` not just `GOOGLE_*`
**Correct names**: `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
**Wrong names**: `GOOGLE_DEVELOPER_TOKEN`, `GOOGLE_CLIENT_ID`, etc.
_#claude-session:2025-11-11_

### Port Conflicts
- FastAPI on 8001 (not 8000) to avoid conflicts
- PostgreSQL on 5433 (not 5432) for same reason

### CORS Errors
- Check `allow_origins` in main.py
- For dev: use `["*"]`
- For production: specify exact frontend URL

### Database Connection
- Wait for PostgreSQL to fully start
- Check DATABASE_URL in .env
- Run `docker-compose logs db` to debug

## Project Patterns

### Cross-Platform Excel Path Handling with OS Detection
**Pattern**: Use `platform.system()` to automatically detect operating system and select appropriate file paths
**Implementation**:
```python
import platform
import os

def get_excel_path():
    windows_path = "c:/Users/Name/Downloads/file.xlsx"
    wsl_path = "/mnt/c/Users/Name/Downloads/file.xlsx"

    system = platform.system().lower()
    if system == "windows":
        return windows_path
    elif system == "linux":
        # Check for WSL
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return wsl_path
        return wsl_path if os.path.exists(wsl_path) else windows_path
    return windows_path
```
**Benefits**: Script works on both Windows and WSL without manual path changes
_#claude-session:2025-11-11_

### Google Ads Client Initialization from .env
**Pattern**: Load Google Ads credentials from environment variables instead of google-ads.yaml
**Implementation**:
```python
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os

load_dotenv()

credentials = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True
}

client = GoogleAdsClient.load_from_dict(credentials)
```
**Benefits**: Credentials managed with other environment variables, easier deployment
_#claude-session:2025-11-11_

### Testing Scripts for Setup Verification
**Pattern**: Create separate test scripts to verify setup before running main script
**Examples**:
- `test_google_ads_init.py` - Tests Google Ads client initialization and credentials
- `test_campaign_processor.py` - Tests all components (client, Excel file, helper functions)
**Benefits**: Catch configuration issues early, provide clear error messages
_#claude-session:2025-11-11_

### No Build Tools Benefits
- Edit HTML/CSS/JS → Save → Refresh browser
- No npm install delays
- No webpack configuration
- No node_modules folder (saves 500MB+)
- Works identically on any machine with Docker

## Script Commands

### Google Ads Campaign Processor
```bash
# Main script execution
python3 campaign_processor.py

# Test Google Ads credentials
python3 test_google_ads_init.py

# Test full setup
python3 test_campaign_processor.py

# Install dependencies
pip3 install -r requirements.txt
```
_#claude-session:2025-11-11_

---
_Created from template: 2025-11-10_
_Updated: 2025-11-11_
