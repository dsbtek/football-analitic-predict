import httpx
from datetime import datetime
from typing import List, Dict, Optional

from app.db import Match, SessionLocal
from app.elo import elo_system, calculate_value_bet
from app.config import settings


class OddsFetcher:
    """
    Fetches odds data from The Odds API and calculates value bets.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the odds fetcher.

        Args:
            api_key: The Odds API key. If None, will try to get from environment.
        """
        self.api_key = api_key or settings.odds_api_key
        if not self.api_key:
            raise ValueError(
                "ODDS_API_KEY must be provided or set as environment variable")

        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "soccer_epl"  # English Premier League
        self.regions = "uk"  # UK bookmakers
        self.markets = "h2h"  # Head-to-head (1X2) markets
        self.odds_format = "decimal"

    async def fetch_upcoming_matches(self) -> List[Dict]:
        """
        Fetch upcoming EPL matches with odds from The Odds API.

        Returns:
            List of match dictionaries with odds data
        """
        url = f"{self.base_url}/sports/{self.sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": self.markets,
            "oddsFormat": self.odds_format,
            "dateFormat": "iso"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching odds: {e}")
            return []

    def parse_team_name(self, team_name: str) -> str:
        """
        Normalize team names to match our Elo rating system.

        Args:
            team_name: Raw team name from API

        Returns:
            Normalized team name
        """
        # Common team name mappings from API to our system
        name_mappings = {
            "Manchester City": "Manchester City",
            "Arsenal": "Arsenal",
            "Liverpool": "Liverpool",
            "Newcastle": "Newcastle United",
            "Newcastle United": "Newcastle United",
            "Manchester United": "Manchester United",
            "Man United": "Manchester United",
            "Tottenham": "Tottenham Hotspur",
            "Spurs": "Tottenham Hotspur",
            "Brighton": "Brighton & Hove Albion",
            "Brighton & Hove Albion": "Brighton & Hove Albion",
            "Aston Villa": "Aston Villa",
            "West Ham": "West Ham United",
            "West Ham United": "West Ham United",
            "Chelsea": "Chelsea",
            "Crystal Palace": "Crystal Palace",
            "Brentford": "Brentford",
            "Fulham": "Fulham",
            "Wolves": "Wolverhampton Wanderers",
            "Wolverhampton": "Wolverhampton Wanderers",
            "Everton": "Everton",
            "Nottingham Forest": "Nottingham Forest",
            "Bournemouth": "Bournemouth",
            "Sheffield United": "Sheffield United",
            "Sheffield Utd": "Sheffield United",
            "Burnley": "Burnley",
            "Luton": "Luton Town",
            "Luton Town": "Luton Town"
        }

        return name_mappings.get(team_name, team_name)

    def calculate_match_values(self, match_data: Dict) -> List[Dict]:
        """
        Calculate value bets for a single match.

        Args:
            match_data: Match data from The Odds API

        Returns:
            List of value bet records for the database
        """
        home_team = self.parse_team_name(match_data['home_team'])
        away_team = self.parse_team_name(match_data['away_team'])
        start_time = datetime.fromisoformat(
            match_data['commence_time'].replace('Z', '+00:00'))

        # Get our model's probabilities
        probabilities = elo_system.calculate_match_probabilities(
            home_team, away_team)

        value_bets = []

        # Process each bookmaker's odds
        for bookmaker in match_data.get('bookmakers', []):
            bookmaker_name = bookmaker['title']

            for market in bookmaker.get('markets', []):
                if market['key'] != 'h2h':
                    continue

                # Extract odds for home/draw/away
                odds_dict = {}
                for outcome in market['outcomes']:
                    if outcome['name'] == home_team:
                        odds_dict['home'] = outcome['price']
                    elif outcome['name'] == away_team:
                        odds_dict['away'] = outcome['price']
                    elif outcome['name'] == 'Draw':
                        odds_dict['draw'] = outcome['price']

                # Calculate value for each outcome
                if all(key in odds_dict for key in ['home', 'draw', 'away']):
                    home_value = calculate_value_bet(
                        probabilities['home_win'],
                        odds_dict['home']
                    )
                    draw_value = calculate_value_bet(
                        probabilities['draw'],
                        odds_dict['draw']
                    )
                    away_value = calculate_value_bet(
                        probabilities['away_win'],
                        odds_dict['away']
                    )

                    # Only store if there's at least one value bet
                    if any(value > 0 for value in [home_value, draw_value, away_value]):
                        value_bets.append({
                            'home': home_team,
                            'away': away_team,
                            'bookmaker': bookmaker_name,
                            'home_odds': odds_dict['home'],
                            'draw_odds': odds_dict['draw'],
                            'away_odds': odds_dict['away'],
                            'value_home': home_value,
                            'value_draw': draw_value,
                            'value_away': away_value,
                            'start_time': start_time
                        })

        return value_bets

    async def fetch_and_store_value_bets(self) -> int:
        """
        Fetch odds, calculate value bets, and store in database.

        Returns:
            Number of value bets found and stored
        """
        matches_data = await self.fetch_upcoming_matches()

        if not matches_data:
            print("No matches data received")
            return 0

        # Clear existing data
        session = SessionLocal()
        try:
            session.query(Match).delete()
            session.commit()

            total_value_bets = 0

            for match_data in matches_data:
                value_bets = self.calculate_match_values(match_data)

                for bet_data in value_bets:
                    match = Match(**bet_data)
                    session.add(match)
                    total_value_bets += 1

            session.commit()
            print(
                f"Stored {total_value_bets} value bets from {len(matches_data)} matches")
            return total_value_bets

        except Exception as e:
            session.rollback()
            print(f"Error storing value bets: {e}")
            return 0
        finally:
            session.close()


# Global instance for the application
odds_fetcher = None


def get_odds_fetcher() -> Optional[OddsFetcher]:
    """Get or create the global odds fetcher instance."""
    global odds_fetcher
    if odds_fetcher is None:
        try:
            odds_fetcher = OddsFetcher()
        except ValueError as e:
            print(f"Warning: {e}")
            # Return None for development when API key is not set
            return None
    return odds_fetcher
