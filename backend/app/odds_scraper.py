"""
Odds scraping fallback system for when API limits are reached.
"""

import asyncio
import httpx
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup
import random

logger = logging.getLogger(__name__)


@dataclass
class ScrapedOdds:
    """Scraped odds data."""
    home_team: str
    away_team: str
    home_odds: float
    draw_odds: float
    away_odds: float
    bookmaker: str
    match_time: Optional[datetime]
    source_url: str


class OddsScraper:
    """Web scraper for odds data as fallback to API."""
    
    def __init__(self):
        self.sources = {
            'oddschecker': {
                'name': 'OddsChecker',
                'base_url': 'https://www.oddschecker.com',
                'football_url': 'https://www.oddschecker.com/football/english/premier-league',
                'enabled': True
            },
            'flashscore': {
                'name': 'FlashScore',
                'base_url': 'https://www.flashscore.com',
                'football_url': 'https://www.flashscore.com/football/england/premier-league/',
                'enabled': True
            }
        }
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        self.scraped_odds_cache = []
        self.last_scrape = None
        self.scrape_interval = 1800  # 30 minutes
        self.rate_limit_delay = 2  # 2 seconds between requests
    
    async def scrape_odds_generic(self, source_config: Dict) -> List[ScrapedOdds]:
        """Generic odds scraping method."""
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                response = await client.get(source_config['football_url'])
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                odds_data = []
                
                # This is a simplified scraper - in production, you'd need
                # specific selectors for each betting site
                odds_data.extend(self._parse_generic_odds(soup, source_config))
                
                return odds_data
                
        except Exception as e:
            logger.error(f"Error scraping odds from {source_config['name']}: {e}")
            return []
    
    def _parse_generic_odds(self, soup: BeautifulSoup, source_config: Dict) -> List[ScrapedOdds]:
        """Parse odds from HTML soup (generic implementation)."""
        odds_data = []
        
        # This is a simplified parser - real implementation would need
        # specific CSS selectors for each betting site
        try:
            # Look for common patterns in betting sites
            match_containers = soup.find_all(['div', 'tr'], class_=re.compile(r'match|fixture|event', re.I))
            
            for container in match_containers[:10]:  # Limit to 10 matches
                # Try to extract team names
                team_elements = container.find_all(['span', 'div', 'td'], class_=re.compile(r'team|name', re.I))
                
                if len(team_elements) >= 2:
                    home_team = self._clean_team_name(team_elements[0].get_text(strip=True))
                    away_team = self._clean_team_name(team_elements[1].get_text(strip=True))
                    
                    # Try to extract odds
                    odds_elements = container.find_all(['span', 'div', 'td'], class_=re.compile(r'odd|price|bet', re.I))
                    
                    if len(odds_elements) >= 3:
                        try:
                            home_odds = self._parse_odds(odds_elements[0].get_text(strip=True))
                            draw_odds = self._parse_odds(odds_elements[1].get_text(strip=True))
                            away_odds = self._parse_odds(odds_elements[2].get_text(strip=True))
                            
                            if all([home_odds, draw_odds, away_odds]):
                                scraped_odds = ScrapedOdds(
                                    home_team=home_team,
                                    away_team=away_team,
                                    home_odds=home_odds,
                                    draw_odds=draw_odds,
                                    away_odds=away_odds,
                                    bookmaker=source_config['name'],
                                    match_time=None,  # Would need specific parsing
                                    source_url=source_config['football_url']
                                )
                                odds_data.append(scraped_odds)
                        except ValueError:
                            continue
                            
        except Exception as e:
            logger.error(f"Error parsing odds HTML: {e}")
        
        return odds_data
    
    def _clean_team_name(self, team_name: str) -> str:
        """Clean and normalize team names."""
        # Remove common prefixes/suffixes
        team_name = re.sub(r'\s*(FC|F\.C\.|United|City)\s*$', '', team_name, flags=re.I)
        team_name = team_name.strip()
        
        # Map to standard EPL team names
        team_mappings = {
            'Man City': 'Manchester City',
            'Man United': 'Manchester United',
            'Man Utd': 'Manchester United',
            'Spurs': 'Tottenham Hotspur',
            'Brighton': 'Brighton & Hove Albion',
            'West Ham': 'West Ham United',
            'Wolves': 'Wolverhampton Wanderers',
            'Newcastle': 'Newcastle United',
            'Forest': 'Nottingham Forest'
        }
        
        return team_mappings.get(team_name, team_name)
    
    def _parse_odds(self, odds_text: str) -> Optional[float]:
        """Parse odds from text."""
        try:
            # Remove any non-numeric characters except decimal point
            odds_clean = re.sub(r'[^\d.]', '', odds_text)
            
            if odds_clean:
                odds = float(odds_clean)
                # Validate odds range
                if 1.0 <= odds <= 100.0:
                    return odds
        except ValueError:
            pass
        
        return None
    
    async def generate_fallback_odds(self) -> List[ScrapedOdds]:
        """Generate realistic fallback odds when scraping fails."""
        # This generates realistic odds based on Elo ratings
        from app.elo import elo_system
        
        fallback_odds = []
        
        # Sample EPL fixtures (in production, get from fixtures API)
        sample_fixtures = [
            ('Manchester City', 'Arsenal'),
            ('Liverpool', 'Chelsea'),
            ('Manchester United', 'Tottenham Hotspur'),
            ('Newcastle United', 'Brighton & Hove Albion'),
            ('Aston Villa', 'West Ham United'),
            ('Crystal Palace', 'Fulham'),
            ('Brentford', 'Wolverhampton Wanderers'),
            ('Everton', 'Bournemouth'),
            ('Nottingham Forest', 'Burnley'),
            ('Sheffield United', 'Luton Town')
        ]
        
        for home_team, away_team in sample_fixtures:
            # Get probabilities from Elo system
            probabilities = elo_system.calculate_match_probabilities(home_team, away_team)
            
            # Convert probabilities to odds (with bookmaker margin)
            margin = 0.05  # 5% bookmaker margin
            
            home_odds = 1 / (probabilities['home_win'] * (1 - margin))
            draw_odds = 1 / (probabilities['draw'] * (1 - margin))
            away_odds = 1 / (probabilities['away_win'] * (1 - margin))
            
            # Add some randomness to make it realistic
            home_odds *= random.uniform(0.95, 1.05)
            draw_odds *= random.uniform(0.95, 1.05)
            away_odds *= random.uniform(0.95, 1.05)
            
            fallback_odds.append(ScrapedOdds(
                home_team=home_team,
                away_team=away_team,
                home_odds=round(home_odds, 2),
                draw_odds=round(draw_odds, 2),
                away_odds=round(away_odds, 2),
                bookmaker='Fallback Generator',
                match_time=datetime.now() + timedelta(days=random.randint(1, 7)),
                source_url='internal://fallback'
            ))
        
        return fallback_odds
    
    async def scrape_all_sources(self) -> List[ScrapedOdds]:
        """Scrape odds from all enabled sources."""
        all_odds = []
        
        for source_key, source_config in self.sources.items():
            if not source_config.get('enabled', True):
                continue
            
            try:
                logger.info(f"Scraping odds from {source_config['name']}")
                source_odds = await self.scrape_odds_generic(source_config)
                all_odds.extend(source_odds)
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Failed to scrape {source_config['name']}: {e}")
        
        # If no odds scraped, use fallback
        if not all_odds:
            logger.info("No odds scraped, generating fallback odds")
            all_odds = await self.generate_fallback_odds()
        
        return all_odds
    
    async def get_odds_data(self, force_scrape: bool = False) -> List[Dict]:
        """Get odds data, using cache if recent."""
        # Check if cache needs refresh
        if (force_scrape or 
            not self.last_scrape or 
            datetime.now() - self.last_scrape > timedelta(seconds=self.scrape_interval)):
            
            try:
                fresh_odds = await self.scrape_all_sources()
                self.scraped_odds_cache = fresh_odds
                self.last_scrape = datetime.now()
                logger.info(f"Updated odds cache with {len(fresh_odds)} items")
            except Exception as e:
                logger.error(f"Failed to update odds cache: {e}")
                # Use fallback if cache update fails
                if not self.scraped_odds_cache:
                    self.scraped_odds_cache = await self.generate_fallback_odds()
        
        # Convert to dictionaries for JSON response
        odds_dicts = []
        for odds in self.scraped_odds_cache:
            odds_dict = {
                'home': odds.home_team,
                'away': odds.away_team,
                'home_odds': odds.home_odds,
                'draw_odds': odds.draw_odds,
                'away_odds': odds.away_odds,
                'bookmaker': odds.bookmaker,
                'match_time': odds.match_time.isoformat() if odds.match_time else None,
                'source_url': odds.source_url,
                'scraped_at': self.last_scrape.isoformat() if self.last_scrape else None
            }
            odds_dicts.append(odds_dict)
        
        return odds_dicts
    
    async def convert_scraped_to_matches(self) -> int:
        """Convert scraped odds to database matches format."""
        from app.db import SessionLocal, Match
        from app.elo import calculate_value_bet
        
        odds_data = await self.get_odds_data()
        
        if not odds_data:
            return 0
        
        session = SessionLocal()
        try:
            # Clear existing scraped data
            session.query(Match).filter(Match.bookmaker.like('%Scraper%')).delete()
            
            matches_added = 0
            
            for odds in odds_data:
                # Calculate value bets using Elo system
                probabilities = elo_system.calculate_match_probabilities(
                    odds['home'], odds['away']
                )
                
                value_home = calculate_value_bet(
                    probabilities['home_win'], odds['home_odds']
                )
                value_draw = calculate_value_bet(
                    probabilities['draw'], odds['draw_odds']
                )
                value_away = calculate_value_bet(
                    probabilities['away_win'], odds['away_odds']
                )
                
                # Only add if there's at least one value bet
                if any(v > 0 for v in [value_home, value_draw, value_away]):
                    match = Match(
                        home=odds['home'],
                        away=odds['away'],
                        bookmaker=f"{odds['bookmaker']} (Scraper)",
                        home_odds=odds['home_odds'],
                        draw_odds=odds['draw_odds'],
                        away_odds=odds['away_odds'],
                        value_home=value_home,
                        value_draw=value_draw,
                        value_away=value_away,
                        start_time=datetime.fromisoformat(odds['match_time']) if odds['match_time'] else None
                    )
                    session.add(match)
                    matches_added += 1
            
            session.commit()
            logger.info(f"Added {matches_added} scraped matches to database")
            return matches_added
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error converting scraped odds to matches: {e}")
            return 0
        finally:
            session.close()


# Global odds scraper instance
odds_scraper = OddsScraper()
