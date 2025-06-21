import os
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # The Odds API Configuration
        self.odds_api_key: Optional[str] = os.getenv('ODDS_API_KEY')

        # Database Configuration
        self.database_url: str = os.getenv(
            'DATABASE_URL', 'sqlite:///./matches.db')

        # API Configuration
        self.api_host: str = os.getenv('API_HOST', '0.0.0.0')
        self.api_port: int = int(os.getenv('API_PORT', '8000'))

        # Frontend Configuration
        self.frontend_url: str = os.getenv(
            'FRONTEND_URL', 'http://localhost:3000')

        # Elo Rating System Configuration
        self.elo_k_factor: float = float(os.getenv('ELO_K_FACTOR', '32'))
        self.elo_home_advantage: float = float(
            os.getenv('ELO_HOME_ADVANTAGE', '100'))

        # Value Betting Configuration
        self.value_bet_threshold: float = float(
            os.getenv('VALUE_BET_THRESHOLD', '0.05'))

    @property
    def is_odds_api_configured(self) -> bool:
        """Check if The Odds API is properly configured."""
        return self.odds_api_key is not None and len(self.odds_api_key.strip()) > 0


# Global settings instance
settings = Settings()
