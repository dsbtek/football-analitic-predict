from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict
from app import db
from app.fetcher import get_odds_fetcher
from app.elo import elo_system
from app.config import settings

app = FastAPI(
    title="Football Analytics Predictor",
    description="EPL value betting system using Elo ratings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Dependency to get database session."""
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Football Analytics Predictor API",
        "version": "1.0.0",
        "endpoints": {
            "/matches/": "Get all value bets",
            "/matches/refresh": "Refresh odds data",
            "/teams/ratings": "Get current team ratings",
            "/health": "Health check"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "football-analytics-api"}


@app.get("/matches/", response_model=List[Dict])
def get_value_matches(db_session: Session = Depends(get_db)):
    """
    Get all current value bets from the database.

    Returns:
        List of value bet opportunities
    """
    try:
        matches = db_session.query(db.Match).all()

        # Convert to dictionaries for JSON response
        result = []
        for match in matches:
            match_dict = {
                "id": match.id,
                "home": match.home,
                "away": match.away,
                "bookmaker": match.bookmaker,
                "home_odds": match.home_odds,
                "draw_odds": match.draw_odds,
                "away_odds": match.away_odds,
                "value_home": round(match.value_home, 2) if match.value_home else 0,
                "value_draw": round(match.value_draw, 2) if match.value_draw else 0,
                "value_away": round(match.value_away, 2) if match.value_away else 0,
                "start_time": match.start_time.isoformat() if match.start_time else None,
                "best_value": max(
                    match.value_home or 0,
                    match.value_draw or 0,
                    match.value_away or 0
                )
            }
            result.append(match_dict)

        # Sort by best value descending
        result.sort(key=lambda x: x["best_value"], reverse=True)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching matches: {str(e)}")


async def refresh_odds_background():
    """Background task to refresh odds data."""
    fetcher = get_odds_fetcher()
    if fetcher:
        try:
            count = await fetcher.fetch_and_store_value_bets()
            print(f"Background refresh completed: {count} value bets stored")
        except Exception as e:
            print(f"Background refresh failed: {e}")
    else:
        print("Cannot refresh odds: API key not configured")


@app.post("/matches/refresh")
async def refresh_matches(background_tasks: BackgroundTasks):
    """
    Refresh odds data from The Odds API and recalculate value bets.

    This endpoint triggers a background task to fetch new data.
    """
    fetcher = get_odds_fetcher()
    if not fetcher:
        raise HTTPException(
            status_code=503,
            detail="Odds API not configured. Please set ODDS_API_KEY environment variable."
        )

    # Add background task to refresh data
    background_tasks.add_task(refresh_odds_background)

    return {
        "message": "Odds refresh started in background",
        "status": "processing"
    }


@app.get("/teams/ratings")
def get_team_ratings():
    """
    Get current Elo ratings for all teams.

    Returns:
        Dictionary of team names and their current Elo ratings
    """
    try:
        ratings = dict(elo_system.ratings)
        # Sort by rating descending
        sorted_ratings = dict(
            sorted(ratings.items(), key=lambda x: x[1], reverse=True))
        return {
            "ratings": sorted_ratings,
            "last_updated": "Static ratings - updates coming in future version"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching ratings: {str(e)}")


@app.get("/matches/probabilities/{home_team}/{away_team}")
def get_match_probabilities(home_team: str, away_team: str):
    """
    Get match outcome probabilities for a specific fixture.

    Args:
        home_team: Name of the home team
        away_team: Name of the away team

    Returns:
        Probabilities for home win, draw, and away win
    """
    try:
        # URL decode team names and replace underscores with spaces
        home_team = home_team.replace("_", " ")
        away_team = away_team.replace("_", " ")

        probabilities = elo_system.calculate_match_probabilities(
            home_team, away_team)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "probabilities": {
                "home_win": round(probabilities["home_win"] * 100, 1),
                "draw": round(probabilities["draw"] * 100, 1),
                "away_win": round(probabilities["away_win"] * 100, 1)
            },
            "home_rating": elo_system.get_team_rating(home_team),
            "away_rating": elo_system.get_team_rating(away_team)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating probabilities: {str(e)}")
