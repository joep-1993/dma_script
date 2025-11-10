# dma-shop-campaigns

FastAPI + PostgreSQL + Docker application with AI integration.

## 🚀 Quick Start

1. **Clone and setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start everything:**
   ```bash
   docker-compose up
   ```

3. **Access the app:**
   Open http://localhost:8001

## 🛠️ Development

- **Backend**: Edit `backend/*.py` - auto-reloads
- **Frontend**: Edit `frontend/*` - refresh browser
- **No build tools**: Just save and refresh!

## 📦 Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: Bootstrap 5 + Vanilla JS (no build!)
- **Database**: PostgreSQL 15
- **AI**: OpenAI API (configurable model)
- **Deploy**: Docker + docker-compose

## 📁 Project Structure

See `cc1/PROJECT_INDEX.md` for detailed structure and documentation.

## 🔧 Common Commands

```bash
docker-compose up          # Start development
docker-compose down        # Stop everything
docker-compose logs -f app # View logs
docker ps                  # Check containers
```

---
Created from [fastapi-docker-cc1-template](https://github.com/YOUR_USERNAME/fastapi-docker-cc1-template)
