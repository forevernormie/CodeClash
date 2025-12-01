import asyncio
from datasets import load_dataset
from app.database import SessionLocal, engine, Base
from app.models import Question
from sqlalchemy import text

async def seed_from_csbench():
    print("🚀 Connecting to Hugging Face Hub...")
    
    # FIX: Changed split from "test" to "mcq"
    dataset = load_dataset("lmms-lab/CSBench_MCQ", split="mcq")
    
    print(f"📦 Found {len(dataset)} questions. Filtering and Writing to Database...")

    # 1. Database Connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Optional: Uncomment to clear old data
        # await session.execute(text("TRUNCATE TABLE questions RESTART IDENTITY"))
        
        count = 0
        for row in dataset:
            # 1. Filter: Ensure it is in English
            if row.get('Language') != 'English':
                continue
            
            # 2. Filter: Ensure we have a valid answer (A, B, C, or D)
            answer = row.get('Answer', '').strip()
            if answer not in ['A', 'B', 'C', 'D']:
                continue

            # 3. Create the Question Object
            new_q = Question(
                title=row['Question'],
                option_a=str(row['A']),
                option_b=str(row['B']),
                option_c=str(row['C']),
                option_d=str(row['D']),
                correct_option=answer,
                category=row['Domain'] 
            )
            
            session.add(new_q)
            count += 1
            
            if count % 100 == 0:
                await session.commit()
                print(f"   ... Inserted {count} questions so far")
        
        await session.commit()
        print(f"✅ SUCCESS! Imported {count} CS questions from CSBench.")

if __name__ == "__main__":
    asyncio.run(seed_from_csbench())