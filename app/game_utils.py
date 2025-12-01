from sqlalchemy import select, func
from . import models, database

# CHANGED: Default limit is now 10
async def get_random_questions(limit: int = 10):
    """Fetches 10 random questions from the database."""
    async with database.SessionLocal() as session:
        result = await session.execute(
            select(models.Question).order_by(func.random()).limit(limit)
        )
        questions = result.scalars().all()
        
        return [
            {
                "id": q.id,
                "question": q.title,
                "options": {
                    "A": q.option_a,
                    "B": q.option_b,
                    "C": q.option_c,
                    "D": q.option_d
                },
                "category": q.category
            }
            for q in questions
        ]

# ... (keep existing imports and functions)

async def check_answer(question_id: int, user_answer: str) -> bool:
    """Verifies if the submitted answer is correct."""
    async with database.SessionLocal() as session:
        # Fetch the specific question
        result = await session.execute(
            select(models.Question).where(models.Question.id == question_id)
        )
        question = result.scalars().first()
        
        if not question:
            return False
            
        # Compare (Make sure both are uppercase/stripped to be safe)
        return question.correct_option.strip().upper() == user_answer.strip().upper()

async def save_match(game_id: str, scores: dict):
    """
    scores dict looks like: {'Manas': '50', 'Devansh': '40'}
    """
    # 1. Parse game_id (game_Manas_Devansh) to get usernames
    _, p1_name, p2_name = game_id.split("_")
    
    async with database.SessionLocal() as session:
        # 2. Find User IDs (We need these for Foreign Keys)
        # In a real app, optimize this lookup. Here we fetch both.
        result = await session.execute(
            select(models.User).where(models.User.username.in_([p1_name, p2_name]))
        )
        users = result.scalars().all()
        
        # Map Name -> User Object
        user_map = {u.username: u for u in users}
        
        if len(user_map) < 2:
            print("❌ Error: Could not find players in DB")
            return

        p1_obj = user_map[p1_name]
        p2_obj = user_map[p2_name]
        
        # 3. Get Scores (Default to 0 if missing)
        s1 = int(scores.get(p1_name, 0))
        s2 = int(scores.get(p2_name, 0))
        
        # 4. Determine Winner
        winner_id = None
        if s1 > s2:
            winner_id = p1_obj.id
        elif s2 > s1:
            winner_id = p2_obj.id
            
        # 5. Save Match
        match = models.Match(
            player1_id=p1_obj.id,
            player2_id=p2_obj.id,
            score1=s1,
            score2=s2,
            winner_id=winner_id
        )
        session.add(match)
        await session.commit()
        print(f"✅ Match Saved: {p1_name} ({s1}) vs {p2_name} ({s2})")