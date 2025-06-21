from app.websocket_manager import (
    connection_manager, real_time_updater, authenticate_websocket,
    handle_websocket_message, start_real_time_updates
)
from app.prediction_engine import prediction_engine, PredictionResult, OddsRequest
from app.news_scraper import news_scraper
from app.odds_scraper import odds_scraper
from app.monitoring import (
    performance_monitor, health_checker, error_tracker,
    create_monitoring_middleware, setup_logging
)
from app.security import (
    get_current_user, rate_limit, get_security_headers,
    user_db, UserCreate, UserLogin, Token, User,
    create_access_token, create_refresh_token, verify_token
)
from app.config import settings
from app.elo import elo_system
from app.fetcher import get_odds_fetcher
from app import db
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, Request, Response, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
import math
import json
import asyncio
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Pydantic models for API responses


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedMatchesResponse(BaseModel):
    matches: List[Dict]
    pagination: PaginationInfo


class CartItem(BaseModel):
    match_id: int
    home: str
    away: str
    bookmaker: str
    bet_type: str  # 'home', 'draw', 'away'
    odds: float
    value: float


class CartResponse(BaseModel):
    items: List[CartItem]
    total_items: int


class AddToCartRequest(BaseModel):
    match_id: int
    bet_type: str  # 'home', 'draw', 'away'


# In-memory cart storage (in production, use Redis or database)
cart_storage: Dict[str, List[CartItem]] = {}

app = FastAPI(
    title="Football Analytics Predictor",
    description="EPL value betting system using Elo ratings",
    version="1.0.0"
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Get environment from settings or default to development
    environment = os.getenv('ENVIRONMENT', 'development')
    headers = get_security_headers(environment)

    for header, value in headers.items():
        response.headers[header] = value
    return response


# Monitoring middleware
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    return await create_monitoring_middleware()(request, call_next)


# Initialize logging
setup_logging()


# Startup event to initialize real-time updates
@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup."""
    asyncio.create_task(start_real_time_updates())


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
            "/auth/register": "Register new user",
            "/auth/login": "User login",
            "/health": "Health check"
        }
    }


# Authentication Endpoints

@app.post("/auth/register", response_model=User)
def register_user(
    user_data: UserCreate,
    _: bool = Depends(rate_limit(max_requests=5, window_seconds=3600))
):
    """Register a new user."""
    try:
        user = user_db.create_user(user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/login", response_model=Token)
def login_user(
    user_credentials: UserLogin,
    _: bool = Depends(rate_limit(max_requests=10, window_seconds=900))
):
    """Authenticate user and return tokens."""
    user = user_db.authenticate_user(
        user_credentials.email,
        user_credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": user.id}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@app.post("/auth/refresh", response_model=Token)
def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_token, token_type="refresh")
        email = payload.get("sub")
        user_id = payload.get("user_id")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new tokens
        new_access_token = create_access_token(
            data={"sub": email, "user_id": user_id}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": email, "user_id": user_id}
        )

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh failed: {str(e)}"
        )


@app.get("/auth/me", response_model=User)
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    user = user_db.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.get("/health")
def health_check():
    """Comprehensive health check endpoint."""
    return health_checker.get_health_status()


@app.get("/metrics")
def get_metrics():
    """Get application performance metrics."""
    return performance_monitor.get_metrics()


@app.get("/errors")
def get_recent_errors(limit: int = Query(10, ge=1, le=50)):
    """Get recent application errors."""
    return {
        "errors": error_tracker.get_recent_errors(limit),
        "total_errors": len(error_tracker.errors)
    }


@app.get("/matches/", response_model=PaginatedMatchesResponse)
def get_value_matches(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        10, ge=1, le=100, description="Number of items per page"),
    db_session: Session = Depends(get_db)
):
    """
    Get paginated value bets from the database.

    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page (1-100)

    Returns:
        Paginated list of value bet opportunities
    """
    try:
        # Get total count
        total_count = db_session.query(db.Match).count()

        # Calculate pagination info
        total_pages = math.ceil(
            total_count / page_size) if total_count > 0 else 1
        offset = (page - 1) * page_size

        # Get paginated matches
        matches_query = db_session.query(
            db.Match).offset(offset).limit(page_size)
        matches = matches_query.all()

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

        # Create pagination info
        pagination_info = PaginationInfo(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )

        return PaginatedMatchesResponse(
            matches=result,
            pagination=pagination_info
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching matches: {str(e)}")


async def refresh_odds_background():
    """Background task to refresh odds data."""
    # Notify clients that refresh is starting
    await real_time_updater.send_odds_refresh_notification()

    fetcher = get_odds_fetcher()
    if fetcher:
        try:
            count = await fetcher.fetch_and_store_value_bets()
            print(f"Background refresh completed: {count} value bets stored")

            # Notify clients that refresh is complete
            await real_time_updater.send_odds_refresh_complete(count)

            # Send updated matches to all clients
            await real_time_updater.check_and_send_updates()

        except Exception as e:
            print(f"Background refresh failed: {e}")
            await real_time_updater.send_system_notification(
                "odds_refresh_error",
                f"Odds refresh failed: {str(e)}",
                "error"
            )
    else:
        print("Cannot refresh odds: API key not configured")
        await real_time_updater.send_system_notification(
            "odds_refresh_error",
            "Cannot refresh odds: API key not configured",
            "warning"
        )


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


# Cart Management Endpoints

def get_cart_key(session_id: str = "default") -> str:
    """Generate cart key for session."""
    return f"cart_{session_id}"


@app.post("/cart/add")
def add_to_cart(
    request: AddToCartRequest,
    session_id: str = Query("default", description="Session ID for cart"),
    db_session: Session = Depends(get_db)
):
    """
    Add a match bet to the cart.

    Args:
        request: Match ID and bet type to add
        session_id: Session identifier for the cart

    Returns:
        Updated cart contents
    """
    try:
        # Get the match from database
        match = db_session.query(db.Match).filter(
            db.Match.id == request.match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        # Validate bet type and get odds/value
        bet_type = request.bet_type.lower()
        if bet_type == "home":
            odds = match.home_odds
            value = match.value_home or 0
        elif bet_type == "draw":
            odds = match.draw_odds
            value = match.value_draw or 0
        elif bet_type == "away":
            odds = match.away_odds
            value = match.value_away or 0
        else:
            raise HTTPException(
                status_code=400, detail="Invalid bet type. Must be 'home', 'draw', or 'away'")

        # Check if value bet exists
        if value <= 0:
            raise HTTPException(
                status_code=400, detail="This is not a value bet")

        cart_key = get_cart_key(session_id)
        if cart_key not in cart_storage:
            cart_storage[cart_key] = []

        # Check for duplicates (same match + bet type)
        existing_item = next(
            (item for item in cart_storage[cart_key]
             if item.match_id == request.match_id and item.bet_type == bet_type),
            None
        )

        if existing_item:
            raise HTTPException(
                status_code=400, detail="This bet is already in your cart")

        # Create cart item
        cart_item = CartItem(
            match_id=match.id,
            home=match.home,
            away=match.away,
            bookmaker=match.bookmaker,
            bet_type=bet_type,
            odds=odds,
            value=round(value, 2)
        )

        cart_storage[cart_key].append(cart_item)

        return CartResponse(
            items=cart_storage[cart_key],
            total_items=len(cart_storage[cart_key])
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding to cart: {str(e)}")


@app.get("/cart/", response_model=CartResponse)
def get_cart(session_id: str = Query("default", description="Session ID for cart")):
    """
    Get current cart contents.

    Args:
        session_id: Session identifier for the cart

    Returns:
        Current cart contents
    """
    cart_key = get_cart_key(session_id)
    items = cart_storage.get(cart_key, [])

    return CartResponse(
        items=items,
        total_items=len(items)
    )


@app.delete("/cart/remove/{match_id}/{bet_type}")
def remove_from_cart(
    match_id: int,
    bet_type: str,
    session_id: str = Query("default", description="Session ID for cart")
):
    """
    Remove a specific bet from the cart.

    Args:
        match_id: ID of the match
        bet_type: Type of bet ('home', 'draw', 'away')
        session_id: Session identifier for the cart

    Returns:
        Updated cart contents
    """
    cart_key = get_cart_key(session_id)
    if cart_key not in cart_storage:
        cart_storage[cart_key] = []

    # Remove the item
    cart_storage[cart_key] = [
        item for item in cart_storage[cart_key]
        if not (item.match_id == match_id and item.bet_type == bet_type.lower())
    ]

    return CartResponse(
        items=cart_storage[cart_key],
        total_items=len(cart_storage[cart_key])
    )


@app.delete("/cart/clear")
def clear_cart(session_id: str = Query("default", description="Session ID for cart")):
    """
    Clear all items from the cart.

    Args:
        session_id: Session identifier for the cart

    Returns:
        Empty cart response
    """
    cart_key = get_cart_key(session_id)
    cart_storage[cart_key] = []

    return CartResponse(items=[], total_items=0)


@app.get("/cart/print")
def get_printable_cart(session_id: str = Query("default", description="Session ID for cart")):
    """
    Get cart contents formatted for printing.

    Args:
        session_id: Session identifier for the cart

    Returns:
        Formatted cart data for printing
    """
    cart_key = get_cart_key(session_id)
    items = cart_storage.get(cart_key, [])

    if not items:
        return {"message": "Cart is empty", "items": []}

    # Format for printing
    formatted_items = []
    total_value = 0

    for item in items:
        formatted_item = {
            "match": f"{item.home} vs {item.away}",
            "bookmaker": item.bookmaker,
            "bet": f"{item.bet_type.title()} Win",
            "odds": f"{item.odds:.2f}",
            "value": f"+{item.value}%",
            "potential_return": f"£{(item.odds * 10):.2f} (£10 stake)"
        }
        formatted_items.append(formatted_item)
        total_value += item.value

    return {
        "title": "🎯 Value Betting Selections",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_selections": len(items),
        "average_value": f"+{(total_value / len(items)):.1f}%",
        "items": formatted_items,
        "disclaimer": "⚠️ Gambling involves risk. Only bet what you can afford to lose."
    }


# WebSocket Endpoints

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time updates.

    Args:
        websocket: WebSocket connection
        token: Optional JWT token for authentication
    """
    # Authenticate user if token provided
    user_id = await authenticate_websocket(websocket, token)

    # Connect to WebSocket manager
    await connection_manager.connect(websocket, user_id)

    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "message": "Connected to Football Analytics real-time updates",
            "authenticated": user_id is not None,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(welcome_message))

        # Send initial data
        await real_time_updater.check_and_send_updates()

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(websocket, message, user_id)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)


@app.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return connection_manager.get_connection_stats()


# Prediction Endpoints

class MatchPredictionRequest(BaseModel):
    home_team: str
    away_team: str
    additional_factors: Optional[Dict] = None


@app.post("/predict/match")
async def predict_match_outcome(request: MatchPredictionRequest):
    """
    Predict outcome for a specific match.

    Args:
        request: Match prediction request with team names and optional factors

    Returns:
        Detailed prediction with confidence and reasoning
    """
    try:
        prediction = prediction_engine.predict_match_outcome(
            request.home_team, request.away_team, request.additional_factors
        )

        return {
            "prediction": {
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "predicted_outcome": prediction.predicted_outcome,
                "confidence": prediction.confidence,
                "probabilities": prediction.probabilities,
                "reasoning": prediction.reasoning,
                "risk_level": prediction.risk_level,
                "expected_value": prediction.expected_value
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch")
async def predict_multiple_matches(
    matches: List[Dict[str, str]],
    db_session: Session = Depends(get_db)
):
    """
    Predict outcomes for multiple matches.

    Args:
        matches: List of matches with 'home' and 'away' team names

    Returns:
        List of predictions for all matches
    """
    try:
        predictions = []

        for match in matches:
            if 'home' not in match or 'away' not in match:
                continue

            prediction = prediction_engine.predict_match_outcome(
                match['home'], match['away']
            )

            predictions.append({
                "match": f"{match['home']} vs {match['away']}",
                "prediction": {
                    "predicted_outcome": prediction.predicted_outcome,
                    "confidence": prediction.confidence,
                    "probabilities": prediction.probabilities,
                    "reasoning": prediction.reasoning,
                    "risk_level": prediction.risk_level
                }
            })

        return {
            "predictions": predictions,
            "total_matches": len(predictions),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.post("/odds/request")
async def request_custom_odds(
    target_odds: float,
    max_matches: int = Query(3, ge=1, le=5),
    risk_tolerance: str = Query(
        "moderate", regex="^(conservative|moderate|aggressive)$"),
    preferred_outcomes: Optional[List[str]] = None,
    db_session: Session = Depends(get_db)
):
    """
    Find match combinations for specific odds requirements.

    Args:
        target_odds: Target odds value (e.g., 3.0)
        max_matches: Maximum number of matches in combination
        risk_tolerance: Risk tolerance level
        preferred_outcomes: Preferred outcomes (home, draw, away)

    Returns:
        List of match combinations that meet the criteria
    """
    try:
        # Get available matches
        matches = db_session.query(db.Match).all()

        if not matches:
            raise HTTPException(
                status_code=404,
                detail="No matches available for odds calculation"
            )

        # Convert to dictionaries
        available_matches = []
        for match in matches:
            match_dict = {
                "id": match.id,
                "home": match.home,
                "away": match.away,
                "bookmaker": match.bookmaker,
                "home_odds": match.home_odds,
                "draw_odds": match.draw_odds,
                "away_odds": match.away_odds,
                "start_time": match.start_time.isoformat() if match.start_time else None
            }
            available_matches.append(match_dict)

        # Create odds request
        odds_request = OddsRequest(
            target_odds=target_odds,
            max_matches=max_matches,
            risk_tolerance=risk_tolerance,
            preferred_outcomes=preferred_outcomes or ['home', 'draw', 'away']
        )

        # Find matching combinations
        combinations = prediction_engine.find_matches_for_odds(
            odds_request, available_matches
        )

        return {
            "request": {
                "target_odds": target_odds,
                "max_matches": max_matches,
                "risk_tolerance": risk_tolerance,
                "preferred_outcomes": preferred_outcomes
            },
            "combinations": combinations,
            "total_found": len(combinations),
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Odds request failed: {str(e)}"
        )


# News Endpoints

@app.get("/news/latest")
async def get_latest_news(
    force_refresh: bool = Query(False, description="Force refresh news cache"),
    limit: int = Query(
        20, ge=1, le=50, description="Number of news items to return")
):
    """
    Get latest football news.

    Args:
        force_refresh: Force refresh of news cache
        limit: Maximum number of news items to return

    Returns:
        List of latest football news items
    """
    try:
        news_items = await news_scraper.get_latest_news(force_refresh)

        return {
            "news": news_items[:limit],
            "total_items": len(news_items),
            "last_updated": news_scraper.last_update.isoformat() if news_scraper.last_update else None,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch news: {str(e)}"
        )


@app.get("/news/team/{team_name}")
async def get_team_news(
    team_name: str,
    limit: int = Query(
        10, ge=1, le=20, description="Number of news items to return")
):
    """
    Get news for a specific team.

    Args:
        team_name: Name of the team
        limit: Maximum number of news items to return

    Returns:
        List of news items related to the team
    """
    try:
        team_news = await news_scraper.get_news_by_team(team_name)

        return {
            "team": team_name,
            "news": team_news[:limit],
            "total_items": len(team_news),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch team news: {str(e)}"
        )


@app.get("/news/category/{category}")
async def get_news_by_category(
    category: str,
    limit: int = Query(
        15, ge=1, le=30, description="Number of news items to return")
):
    """
    Get news by category.

    Args:
        category: News category (transfer, match, injury, general)
        limit: Maximum number of news items to return

    Returns:
        List of news items in the specified category
    """
    # Validate category parameter
    valid_categories = ['transfer', 'match', 'injury', 'general']
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        )

    try:
        category_news = await news_scraper.get_news_by_category(category)

        return {
            "category": category,
            "news": category_news[:limit],
            "total_items": len(category_news),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch category news: {str(e)}"
        )


# Odds Scraper Endpoints

@app.get("/odds/scraped")
async def get_scraped_odds(
    force_scrape: bool = Query(
        False, description="Force refresh scraped odds"),
    limit: int = Query(20, ge=1, le=50, description="Number of odds to return")
):
    """
    Get odds from web scraping (fallback system).

    Args:
        force_scrape: Force refresh of scraped odds
        limit: Maximum number of odds to return

    Returns:
        List of scraped odds data
    """
    try:
        odds_data = await odds_scraper.get_odds_data(force_scrape)

        return {
            "odds": odds_data[:limit],
            "total_items": len(odds_data),
            "last_scraped": odds_scraper.last_scrape.isoformat() if odds_scraper.last_scrape else None,
            "source": "web_scraping",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scraped odds: {str(e)}"
        )


@app.post("/odds/scrape-to-db")
async def convert_scraped_odds_to_matches():
    """
    Convert scraped odds to database matches format.

    Returns:
        Number of matches added to database
    """
    try:
        matches_added = await odds_scraper.convert_scraped_to_matches()

        return {
            "matches_added": matches_added,
            "message": f"Successfully added {matches_added} matches from scraped odds",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert scraped odds: {str(e)}"
        )
