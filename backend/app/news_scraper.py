"""
Football news scraper for real-time news updates.
"""

import asyncio
import httpx
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Football news item."""
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime
    category: str  # 'transfer', 'match', 'injury', 'general'
    teams_mentioned: List[str]


class FootballNewsScraper:
    """Scraper for football news from multiple sources."""
    
    def __init__(self):
        self.sources = {
            'bbc_sport': {
                'name': 'BBC Sport',
                'rss_url': 'http://feeds.bbci.co.uk/sport/football/rss.xml',
                'type': 'rss'
            },
            'sky_sports': {
                'name': 'Sky Sports',
                'rss_url': 'http://www.skysports.com/rss/0,20514,11661,00.xml',
                'type': 'rss'
            },
            'espn': {
                'name': 'ESPN',
                'rss_url': 'https://www.espn.com/espn/rss/soccer/news',
                'type': 'rss'
            },
            'goal': {
                'name': 'Goal.com',
                'rss_url': 'https://www.goal.com/feeds/en/news',
                'type': 'rss'
            }
        }
        
        # EPL team names for filtering
        self.epl_teams = [
            "Manchester City", "Arsenal", "Liverpool", "Newcastle United",
            "Manchester United", "Tottenham Hotspur", "Brighton & Hove Albion",
            "Aston Villa", "West Ham United", "Chelsea", "Crystal Palace",
            "Brentford", "Fulham", "Wolverhampton Wanderers", "Everton",
            "Nottingham Forest", "Bournemouth", "Sheffield United",
            "Burnley", "Luton Town"
        ]
        
        # Alternative team names for better matching
        self.team_aliases = {
            "Man City": "Manchester City",
            "Man United": "Manchester United",
            "Man Utd": "Manchester United",
            "Spurs": "Tottenham Hotspur",
            "Brighton": "Brighton & Hove Albion",
            "West Ham": "West Ham United",
            "Wolves": "Wolverhampton Wanderers",
            "Newcastle": "Newcastle United",
            "Forest": "Nottingham Forest"
        }
        
        self.news_cache = []
        self.last_update = None
        self.update_interval = 300  # 5 minutes
    
    async def fetch_news_from_rss(self, source_config: Dict) -> List[NewsItem]:
        """Fetch news from RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(source_config['rss_url'])
                response.raise_for_status()
                
                # Parse RSS feed
                feed = feedparser.parse(response.text)
                news_items = []
                
                for entry in feed.entries[:10]:  # Limit to 10 latest items
                    # Extract publication date
                    pub_date = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    # Extract teams mentioned
                    teams_mentioned = self._extract_teams_from_text(
                        f"{entry.title} {getattr(entry, 'summary', '')}"
                    )
                    
                    # Categorize news
                    category = self._categorize_news(entry.title, getattr(entry, 'summary', ''))
                    
                    news_item = NewsItem(
                        title=entry.title,
                        summary=getattr(entry, 'summary', '')[:200] + "..." if len(getattr(entry, 'summary', '')) > 200 else getattr(entry, 'summary', ''),
                        url=entry.link,
                        source=source_config['name'],
                        published_at=pub_date,
                        category=category,
                        teams_mentioned=teams_mentioned
                    )
                    
                    # Only include EPL-related news
                    if teams_mentioned or self._is_epl_related(entry.title):
                        news_items.append(news_item)
                
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching news from {source_config['name']}: {e}")
            return []
    
    def _extract_teams_from_text(self, text: str) -> List[str]:
        """Extract EPL team names from text."""
        teams_found = []
        text_lower = text.lower()
        
        # Check for full team names
        for team in self.epl_teams:
            if team.lower() in text_lower:
                teams_found.append(team)
        
        # Check for aliases
        for alias, full_name in self.team_aliases.items():
            if alias.lower() in text_lower and full_name not in teams_found:
                teams_found.append(full_name)
        
        return list(set(teams_found))  # Remove duplicates
    
    def _categorize_news(self, title: str, summary: str) -> str:
        """Categorize news based on content."""
        text = f"{title} {summary}".lower()
        
        transfer_keywords = ['transfer', 'signing', 'deal', 'contract', 'move', 'join', 'bid']
        injury_keywords = ['injury', 'injured', 'out', 'sidelined', 'fitness', 'recovery']
        match_keywords = ['match', 'game', 'fixture', 'vs', 'against', 'preview', 'report']
        
        if any(keyword in text for keyword in transfer_keywords):
            return 'transfer'
        elif any(keyword in text for keyword in injury_keywords):
            return 'injury'
        elif any(keyword in text for keyword in match_keywords):
            return 'match'
        else:
            return 'general'
    
    def _is_epl_related(self, title: str) -> bool:
        """Check if news is EPL-related even without specific team mentions."""
        epl_keywords = [
            'premier league', 'epl', 'english football', 'top flight',
            'premier league table', 'premier league news'
        ]
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in epl_keywords)
    
    async def fetch_all_news(self) -> List[NewsItem]:
        """Fetch news from all sources."""
        all_news = []
        
        # Fetch from all RSS sources
        tasks = []
        for source_key, source_config in self.sources.items():
            if source_config['type'] == 'rss':
                tasks.append(self.fetch_news_from_rss(source_config))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"News fetch failed: {result}")
        
        # Sort by publication date (newest first)
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        
        # Remove duplicates based on title similarity
        unique_news = self._remove_duplicates(all_news)
        
        return unique_news[:20]  # Return top 20 news items
    
    def _remove_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate news items based on title similarity."""
        unique_items = []
        seen_titles = set()
        
        for item in news_items:
            # Create a normalized title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', item.title.lower())
            normalized_title = ' '.join(normalized_title.split())
            
            # Check if we've seen a similar title
            is_duplicate = False
            for seen_title in seen_titles:
                # Simple similarity check (can be improved)
                if self._calculate_similarity(normalized_title, seen_title) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_items.append(item)
                seen_titles.add(normalized_title)
        
        return unique_items
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simplified)."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def update_news_cache(self):
        """Update the news cache."""
        try:
            fresh_news = await self.fetch_all_news()
            self.news_cache = fresh_news
            self.last_update = datetime.now()
            logger.info(f"Updated news cache with {len(fresh_news)} items")
        except Exception as e:
            logger.error(f"Failed to update news cache: {e}")
    
    async def get_latest_news(self, force_refresh: bool = False) -> List[Dict]:
        """Get latest news, using cache if recent."""
        # Check if cache needs refresh
        if (force_refresh or 
            not self.last_update or 
            datetime.now() - self.last_update > timedelta(seconds=self.update_interval)):
            await self.update_news_cache()
        
        # Convert to dictionaries for JSON response
        news_dicts = []
        for item in self.news_cache:
            news_dict = {
                'title': item.title,
                'summary': item.summary,
                'url': item.url,
                'source': item.source,
                'published_at': item.published_at.isoformat(),
                'category': item.category,
                'teams_mentioned': item.teams_mentioned,
                'time_ago': self._format_time_ago(item.published_at)
            }
            news_dicts.append(news_dict)
        
        return news_dicts
    
    def _format_time_ago(self, published_at: datetime) -> str:
        """Format time ago string."""
        now = datetime.now()
        diff = now - published_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    async def get_news_by_team(self, team_name: str) -> List[Dict]:
        """Get news filtered by specific team."""
        all_news = await self.get_latest_news()
        team_news = [
            news for news in all_news 
            if team_name in news['teams_mentioned'] or team_name.lower() in news['title'].lower()
        ]
        return team_news
    
    async def get_news_by_category(self, category: str) -> List[Dict]:
        """Get news filtered by category."""
        all_news = await self.get_latest_news()
        category_news = [
            news for news in all_news 
            if news['category'] == category
        ]
        return category_news


# Global news scraper instance
news_scraper = FootballNewsScraper()
