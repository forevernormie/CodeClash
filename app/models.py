from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Game specific stats
    rating = Column(Integer, default=1000) # ELO rating
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False) # The question text
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    
    # We store the answer as 'A', 'B', 'C', or 'D'
    correct_option = Column(String, nullable=False) 
    
    # Category: 'Complexity', 'Debugging', 'Concepts'
    category = Column(String, index=True)


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who played? (We store User IDs to link back to the User table)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # What was the score?
    score1 = Column(Integer, default=0)
    score2 = Column(Integer, default=0)
    
    # Who won? (Nullable, because it could be a draw)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    played_at = Column(DateTime(timezone=True), server_default=func.now())