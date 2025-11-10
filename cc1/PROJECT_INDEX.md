# PROJECT INDEX
_Project structure and technical specs. Update when: creating files, adding dependencies, defining schemas._

## Stack
Backend: FastAPI (Python 3.11) | Frontend: Bootstrap 5 + Vanilla JS | Database: PostgreSQL 15 | AI: OpenAI API | Deploy: Docker + docker-compose

## Directory Structure
```
dma-shop-campaigns/
├── cc1/                   # CC1 documentation
│   ├── TASKS.md          # Task tracking
│   ├── LEARNINGS.md      # Knowledge capture
│   ├── BACKLOG.md        # Future planning
│   └── PROJECT_INDEX.md  # This file
├── backend/
│   ├── main.py           # FastAPI app with CORS
│   ├── database.py       # PostgreSQL connection
│   └── gpt_service.py    # AI integration
├── frontend/
│   ├── index.html        # Main page (Bootstrap CDN)
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── app.js        # Vanilla JavaScript
├── docker-compose.yml    # Service orchestration
├── Dockerfile           # Python container
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
├── .env                # Local environment (git ignored)
├── .gitignore          # Version control excludes
├── README.md           # Quick start guide
└── CLAUDE.md           # Claude Code instructions
```

## Environment Variables

### Required
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

## API Endpoints
- `GET /` - System status
- `GET /api/health` - Health check
- `POST /api/generate` - AI text generation
- `GET /static/*` - Frontend files

---
_Last updated: 2025-11-10_
