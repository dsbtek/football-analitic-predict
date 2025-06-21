# 📈 Sports Betting Value Predictor (EPL)

This is a full-stack application that fetches English Premier League odds, calculates match outcome probabilities using an Elo rating model, and highlights **value bets** where the bettor has a statistical edge over the bookmaker.

## 🔧 Stack

-   **Backend**: FastAPI + SQLite + Python
-   **Frontend**: React
-   **Data Source**: [The Odds API](https://the-odds-api.com)
-   **Containerization**: Docker & Docker Compose

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

### ⚙️ 2. Set Up Environment Variables

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
ODDS_API_KEY=your_actual_api_key_here
```

### 🐳 3. Build and Run with Docker

```bash
docker-compose up --build
```

-   **React frontend**: `http://localhost:3000`
-   **FastAPI backend**: `http://localhost:8000`
-   **API documentation**: `http://localhost:8000/docs`
-   **SQLite DB**: `backend/app/matches.db`

### 🧪 4. Test the System

Run the test suite to verify everything works:

```bash
cd backend
python test_elo.py
```

## 🧠 How It Works

1. **Odds Fetcher** hits The Odds API for upcoming EPL matches.
2. **Elo Model** assigns win/draw/loss probabilities to each match.
3. **Value Bets** are detected by comparing your model's probabilities vs bookmaker's implied odds.
4. Data is stored in SQLite and exposed via paginated APIs.
5. **Frontend** displays value bets with cart functionality and printing options.

## ✨ Features

### 🎯 Value Betting

-   **Elo Rating System**: Advanced team strength calculations
-   **Real-time Odds**: Live data from The Odds API
-   **Value Detection**: Automatic identification of profitable bets
-   **Multiple Bookmakers**: Compare odds across different providers

### 🛒 Cart System

-   **Add to Cart**: Select your favorite value bets
-   **Duplicate Prevention**: Automatic detection of duplicate selections
-   **Print Functionality**: Generate printable betting slips
-   **Session Management**: Cart persists during your session

### 📊 User Interface

-   **Pagination**: Navigate through large datasets efficiently
-   **Filtering**: Filter by bet type (home/draw/away)
-   **Responsive Design**: Works on desktop and mobile
-   **Real-time Updates**: Refresh odds with one click

## 📊 API Endpoints

| Endpoint                   | Method | Description               |
| -------------------------- | ------ | ------------------------- |
| `/matches/`                | GET    | Get paginated value bets  |
| `/matches/refresh`         | POST   | Refresh odds data         |
| `/teams/ratings`           | GET    | Get current Elo ratings   |
| `/cart/add`                | POST   | Add bet to cart           |
| `/cart/`                   | GET    | Get cart contents         |
| `/cart/remove/{id}/{type}` | DELETE | Remove bet from cart      |
| `/cart/clear`              | DELETE | Clear entire cart         |
| `/cart/print`              | GET    | Get printable cart format |

## 💡 Future Improvements

-   Add **automatic Elo rating updates** from match history
-   Include **Kelly Criterion** for bet sizing
-   Deploy with **NGINX + HTTPS**
-   Add **authentication** and user dashboards

## 🧠 Author

Built by **Binary Brainwaves Nigeria Limited** — betting like a data scientist ⚽📊
