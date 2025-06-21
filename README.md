
# 📈 Sports Betting Value Predictor (EPL)

This is a full-stack application that fetches English Premier League odds, calculates match outcome probabilities using an Elo rating model, and highlights **value bets** where the bettor has a statistical edge over the bookmaker.

## 🔧 Stack

- **Backend**: FastAPI + SQLite + Python
- **Frontend**: React
- **Data Source**: [The Odds API](https://the-odds-api.com)
- **Containerization**: Docker & Docker Compose

## 📁 Project Structure

```
project-root/
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── db.py            # SQLite models & session
│   │   ├── elo.py           # Elo rating logic
│   │   └── fetcher.py       # Fetch + save odds from The Odds API
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── (React App files)
│   └── Dockerfile
│
└── docker-compose.yml
└── README.md
```

## 🚀 Getting Started

### 🔐 1. Get Your Odds API Key

Register and get a free API key at:  
👉 [https://the-odds-api.com](https://the-odds-api.com)

Set it in your `.env` file or directly in the code.

### ⚙️ 2. Build and Run the Stack

```bash
docker-compose up --build
```

- React frontend runs on: `http://localhost:3000`
- FastAPI backend runs on: `http://localhost:8000`
- SQLite DB stored in `backend/app/matches.db`

## 🧠 How It Works

1. **Odds Fetcher** hits The Odds API for upcoming EPL matches.
2. **Elo Model** assigns win/draw/loss probabilities to each match.
3. **Value Bets** are detected by comparing your model's probabilities vs bookmaker's implied odds.
4. Data is stored in SQLite and exposed via the `/matches/` API.
5. **Frontend** fetches and displays value bets in a table.

## 📊 API Endpoint

| Endpoint | Method | Description         |
|----------|--------|---------------------|
| `/matches/` | GET    | Returns all value bets |

## 💡 Future Improvements

- Add **automatic Elo rating updates** from match history
- Include **Kelly Criterion** for bet sizing
- Deploy with **NGINX + HTTPS**
- Add **authentication** and user dashboards

## 🧠 Author

Built by **Muhammad** — betting like a data scientist ⚽📊
