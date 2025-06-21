"""
Enhanced database management with connection pooling, migrations, and validation.
"""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Enhanced database manager with connection pooling and migrations."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.SessionLocal = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Set up database engine with proper configuration."""
        if self.database_url.startswith("sqlite"):
            # SQLite specific configuration
            self.engine = create_engine(
                self.database_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 20,
                    "isolation_level": None
                },
                poolclass=StaticPool,
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            
            # Enable WAL mode for better concurrency
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        else:
            # PostgreSQL/MySQL configuration
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self):
        """Get database session with proper error handling."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_backup(self, backup_path: str = None) -> str:
        """Create database backup."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backups/backup_{timestamp}.db"
        
        # Create backup directory
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        if self.database_url.startswith("sqlite"):
            # SQLite backup
            db_path = self.database_url.replace("sqlite:///", "")
            shutil.copy2(db_path, backup_path)
        else:
            # For other databases, you'd use pg_dump, mysqldump, etc.
            logger.warning("Backup not implemented for non-SQLite databases")
            return None
        
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
    
    def cleanup_old_backups(self, days_to_keep: int = 7):
        """Clean up old backup files."""
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_date:
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {filename}")
    
    def validate_connection(self) -> bool:
        """Validate database connection."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection validation failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_session() as session:
                if self.database_url.startswith("sqlite"):
                    # SQLite specific stats
                    result = session.execute(text("""
                        SELECT 
                            (SELECT COUNT(*) FROM matches) as match_count,
                            (SELECT COUNT(*) FROM sqlite_master WHERE type='table') as table_count
                    """)).fetchone()
                    
                    return {
                        "match_count": result[0] if result else 0,
                        "table_count": result[1] if result else 0,
                        "database_type": "SQLite"
                    }
                else:
                    # Generic stats for other databases
                    return {"database_type": "Other", "stats": "Not implemented"}
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}


class DataValidator:
    """Validate data before database operations."""
    
    @staticmethod
    def validate_match_data(match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate match data before insertion."""
        errors = []
        
        # Required fields
        required_fields = ['home', 'away', 'bookmaker', 'home_odds', 'draw_odds', 'away_odds']
        for field in required_fields:
            if field not in match_data or match_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate odds
        odds_fields = ['home_odds', 'draw_odds', 'away_odds']
        for field in odds_fields:
            if field in match_data:
                try:
                    odds = float(match_data[field])
                    if odds <= 1.0 or odds > 1000:
                        errors.append(f"Invalid odds for {field}: {odds}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid odds format for {field}")
        
        # Validate team names
        for team_field in ['home', 'away']:
            if team_field in match_data:
                team_name = match_data[team_field]
                if not isinstance(team_name, str) or len(team_name.strip()) == 0:
                    errors.append(f"Invalid team name for {team_field}")
                elif len(team_name) > 100:
                    errors.append(f"Team name too long for {team_field}")
        
        # Validate bookmaker
        if 'bookmaker' in match_data:
            bookmaker = match_data['bookmaker']
            if not isinstance(bookmaker, str) or len(bookmaker.strip()) == 0:
                errors.append("Invalid bookmaker name")
            elif len(bookmaker) > 100:
                errors.append("Bookmaker name too long")
        
        # Validate value bets
        value_fields = ['value_home', 'value_draw', 'value_away']
        for field in value_fields:
            if field in match_data and match_data[field] is not None:
                try:
                    value = float(match_data[field])
                    if value < 0 or value > 100:
                        errors.append(f"Invalid value percentage for {field}: {value}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid value format for {field}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "validated_data": match_data if len(errors) == 0 else None
        }
    
    @staticmethod
    def sanitize_match_data(match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize match data."""
        sanitized = {}
        
        # Sanitize string fields
        string_fields = ['home', 'away', 'bookmaker']
        for field in string_fields:
            if field in match_data and match_data[field]:
                sanitized[field] = str(match_data[field]).strip()[:100]
        
        # Sanitize numeric fields
        numeric_fields = ['home_odds', 'draw_odds', 'away_odds', 'value_home', 'value_draw', 'value_away']
        for field in numeric_fields:
            if field in match_data and match_data[field] is not None:
                try:
                    sanitized[field] = round(float(match_data[field]), 2)
                except (ValueError, TypeError):
                    pass  # Skip invalid values
        
        # Copy other fields
        for field, value in match_data.items():
            if field not in string_fields and field not in numeric_fields:
                sanitized[field] = value
        
        return sanitized


class DatabaseMigration:
    """Handle database migrations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_current_version(self) -> int:
        """Get current database schema version."""
        try:
            with self.db_manager.get_session() as session:
                # Create migration table if it doesn't exist
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                result = session.execute(text(
                    "SELECT MAX(version) FROM schema_migrations"
                )).fetchone()
                
                return result[0] if result and result[0] else 0
        except Exception as e:
            logger.error(f"Failed to get schema version: {e}")
            return 0
    
    def apply_migration(self, version: int, sql: str):
        """Apply a database migration."""
        try:
            with self.db_manager.get_session() as session:
                # Execute migration SQL
                session.execute(text(sql))
                
                # Record migration
                session.execute(text(
                    "INSERT INTO schema_migrations (version) VALUES (:version)"
                ), {"version": version})
                
                logger.info(f"Applied migration version {version}")
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            raise
    
    def run_migrations(self):
        """Run all pending migrations."""
        current_version = self.get_current_version()
        
        migrations = [
            (1, """
                CREATE INDEX IF NOT EXISTS idx_matches_start_time ON matches(start_time);
                CREATE INDEX IF NOT EXISTS idx_matches_bookmaker ON matches(bookmaker);
                CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home, away);
            """),
            (2, """
                ALTER TABLE matches ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE matches ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
        ]
        
        for version, sql in migrations:
            if version > current_version:
                try:
                    self.apply_migration(version, sql)
                except Exception as e:
                    logger.error(f"Migration {version} failed: {e}")
                    break


# Global database manager instance
db_manager = DatabaseManager()
data_validator = DataValidator()
migration_manager = DatabaseMigration(db_manager)
