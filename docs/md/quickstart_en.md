# 🚀 Quick Start Guide (5 Minutes)

This guide will help you get started with MathModelAgent in 5 minutes.

## Prerequisites

- **Docker** and **Docker Compose** (Recommended) OR
- **Python 3.10+**, **Node.js 18+**, **Redis**

## Option 1: Docker Quick Start (Recommended ⭐)

### Step 1: Clone the Repository

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### Step 2: Start Services

```bash
docker-compose up
```

Wait for all services to start (about 1-2 minutes).

### Step 3: Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

### Step 4: Configure API Key

1. Click the avatar icon in the left sidebar
2. Enter your API Key (supports DeepSeek, OpenAI, etc.)
3. Click Save

### Step 5: Run Your First Example

1. In the chat interface, enter a mathematical modeling problem:
   ```
   Problem: A farm has 50 acres of land and can plant corn and wheat.
   Corn: 800kg/acre yield, 500 yuan cost, 2 yuan/kg selling price
   Wheat: 600kg/acre yield, 400 yuan cost, 2.5 yuan/kg selling price
   How to allocate planting area to maximize profit?
   ```
2. Click send and wait for AI to analyze, model, solve, and generate the paper

✅ **Done!** You've successfully run MathModelAgent!

---

## Option 2: Local Deployment (Developers)

### Step 1: Clone the Repository

```bash
git clone https://github.com/leozer534-coder/math-modeling-agent.git
cd math-modeling-agent
```

### Step 2: Start Redis

**macOS:**
```bash
brew install redis
redis-server
```

**Linux:**
```bash
sudo apt-get install redis-server
redis-server
```

**Windows:**
Download and run [Redis for Windows](https://github.com/microsoftarchive/redis/releases)

### Step 3: Configure Backend

```bash
cd backend

# Copy environment configuration
cp .env.example .env.dev

# Edit .env.dev and set your API Key
# At minimum, set COORDINATOR_API_KEY
```

### Step 4: Install Backend Dependencies

```bash
# Recommended: use uv (faster)
pip install uv
uv sync

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 5: Start Backend

```bash
# macOS/Linux:
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120 --reload

# Windows:
set ENV=DEV
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 60 --ws-ping-timeout 120
```

### Step 6: Start Frontend

```bash
cd frontend

# Install pnpm (if not installed)
npm install -g pnpm

# Install dependencies
pnpm i

# Start development server
pnpm run dev
```

### Step 7: Access and Configure

Open http://localhost:5173 and configure API Key as described above

---

## Common Issues

### Q: Can't access frontend after startup?

**A:** Check if backend and Redis are running:
```bash
# Check Docker container status
docker-compose ps

# Check backend logs
docker-compose logs backend
```

### Q: Which API Key model should I use?

**A:** **DeepSeek** is recommended for cost-effectiveness. You can also use OpenAI, Claude, etc. Configure in `.env.dev`:
```env
COORDINATOR_API_KEY=sk-your-key
COORDINATOR_MODEL=deepseek/deepseek-chat
COORDINATOR_BASE_URL=https://api.deepseek.com
```

### Q: Code execution failed?

**A:** Check if Jupyter is properly installed:
```bash
# In backend virtual environment
pip install jupyter
```

### Q: How to view generated papers?

**A:** Generated files are saved in `backend/project/work_dir/xxx/`:
- `notebook.ipynb` - Code execution records
- `res.md` - Final paper (Markdown format)

---

## Next Steps

- 📖 Check [Detailed Deployment Guide](./deployment.md) for more deployment options
- 📚 View [Example Cases](./examples.md) for more usage scenarios
- ❓ Check [FAQ](./faq.md) for common problems
- 🎥 Watch [Video Tutorials](https://www.bilibili.com/) (Coming soon)

---

**Need Help?** Join our community:
- QQ Group: 699970403
- [Discord](https://discord.gg/3Jmpqg5J)
- [GitHub Issues](https://github.com/leozer534-coder/math-modeling-agent/issues)
