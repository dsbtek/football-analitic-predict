from typing import Dict


class EloRatingSystem:
    """
    Elo rating system for football teams to calculate match outcome probabilities.
    """

    def __init__(self, k_factor: float = 32, home_advantage: float = 100):
        """
        Initialize the Elo rating system.

        Args:
            k_factor: The K-factor determines how much ratings change after each match
            home_advantage: Points added to home team's rating for calculations
        """
        self.k_factor = k_factor
        self.home_advantage = home_advantage

        # Initial EPL team ratings (based on recent performance and historical strength)
        self.ratings: Dict[str, float] = {
            "Manchester City": 2100.0,
            "Arsenal": 2050.0,
            "Liverpool": 2040.0,
            "Newcastle United": 1950.0,
            "Manchester United": 1920.0,
            "Tottenham Hotspur": 1900.0,
            "Brighton & Hove Albion": 1850.0,
            "Aston Villa": 1840.0,
            "West Ham United": 1800.0,
            "Chelsea": 1790.0,
            "Crystal Palace": 1750.0,
            "Brentford": 1740.0,
            "Fulham": 1730.0,
            "Wolverhampton Wanderers": 1720.0,
            "Everton": 1700.0,
            "Nottingham Forest": 1690.0,
            "Bournemouth": 1680.0,
            "Sheffield United": 1650.0,
            "Burnley": 1640.0,
            "Luton Town": 1600.0
        }

    def get_team_rating(self, team_name: str) -> float:
        """Get the current Elo rating for a team."""
        return self.ratings.get(team_name, 1500)  # Default rating if team not found

    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate expected score for team A against team B.

        Args:
            rating_a: Elo rating of team A
            rating_b: Elo rating of team B

        Returns:
            Expected score (0-1) for team A
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def calculate_match_probabilities(self, home_team: str, away_team: str) -> Dict[str, float]:
        """
        Calculate win/draw/loss probabilities for a match.

        Args:
            home_team: Name of the home team
            away_team: Name of the away team

        Returns:
            Dictionary with probabilities for 'home_win', 'draw', 'away_win'
        """
        home_rating = self.get_team_rating(home_team) + self.home_advantage
        away_rating = self.get_team_rating(away_team)

        # Calculate expected score for home team
        home_expected = self.calculate_expected_score(home_rating, away_rating)
        away_expected = 1 - home_expected

        # Convert to win/draw/loss probabilities using a model that accounts for draws
        # This is a simplified model - in practice, you might use more sophisticated approaches

        # Adjust for draw probability (draws are more likely in football)
        draw_factor = 0.25  # Base draw probability

        # Calculate raw probabilities
        home_win_raw = home_expected * (1 - draw_factor)
        away_win_raw = away_expected * (1 - draw_factor)
        draw_raw = draw_factor + (0.5 - abs(home_expected - 0.5)) * 0.2

        # Normalize probabilities to sum to 1
        total = home_win_raw + draw_raw + away_win_raw

        return {
            'home_win': home_win_raw / total,
            'draw': draw_raw / total,
            'away_win': away_win_raw / total
        }

    def update_ratings(self, home_team: str, away_team: str, result: str) -> None:
        """
        Update team ratings after a match result.

        Args:
            home_team: Name of the home team
            away_team: Name of the away team
            result: Match result ('home_win', 'draw', 'away_win')
        """
        home_rating = self.get_team_rating(home_team)
        away_rating = self.get_team_rating(away_team)

        # Calculate expected scores (without home advantage for rating updates)
        home_expected = self.calculate_expected_score(home_rating, away_rating)
        away_expected = 1 - home_expected

        # Determine actual scores based on result
        if result == 'home_win':
            home_actual, away_actual = 1.0, 0.0
        elif result == 'away_win':
            home_actual, away_actual = 0.0, 1.0
        else:  # draw
            home_actual, away_actual = 0.5, 0.5

        # Update ratings
        home_new = home_rating + self.k_factor * (home_actual - home_expected)
        away_new = away_rating + self.k_factor * (away_actual - away_expected)

        self.ratings[home_team] = home_new
        self.ratings[away_team] = away_new


def calculate_value_bet(model_probability: float, bookmaker_odds: float, threshold: float = 0.05) -> float:
    """
    Calculate if a bet has positive expected value.

    Args:
        model_probability: Our model's probability for the outcome (0-1)
        bookmaker_odds: Bookmaker's decimal odds
        threshold: Minimum edge required to consider it a value bet

    Returns:
        Expected value percentage (positive means value bet)
    """
    if bookmaker_odds <= 1.0:
        return 0.0

    implied_probability = 1 / bookmaker_odds
    edge = model_probability - implied_probability

    # Only return positive value if edge exceeds threshold
    if edge > threshold:
        expected_value = (model_probability *
                          (bookmaker_odds - 1)) - (1 - model_probability)
        return expected_value * 100  # Return as percentage

    return 0.0


# Global instance for the application
elo_system = EloRatingSystem()
