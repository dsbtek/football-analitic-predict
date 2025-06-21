from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./matches.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    home = Column(String)
    away = Column(String)
    bookmaker = Column(String)
    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)
    value_home = Column(Float)
    value_draw = Column(Float)
    value_away = Column(Float)
    start_time = Column(DateTime)


Base.metadata.create_all(bind=engine)
