from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
import json

from . import models, schemas, auth, database, matchmaker, game_utils
from . import game_state

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(title="CodeClash API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UPGRADED CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Dictionary: Maps "username" -> WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            websocket = self.active_connections[username]
            await websocket.send_text(json.dumps(message))
    # Inside ConnectionManager class
    async def broadcast_to_user(self, message: dict, username: str):
        if username in self.active_connections:
            websocket = self.active_connections[username]
            await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

# --- ROUTES ---

@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User).where(
        (models.User.email == user.email) | (models.User.username == user.username)
    ))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/login")
async def login(user_credentials: schemas.UserLogin, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User).where(models.User.username == user_credentials.username))
    user = result.scalars().first()
    if not user or not auth.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- THE REAL-TIME GAME SOCKET ---

@app.websocket("/ws/matchmaking/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    
    try:
        await manager.send_personal_message({"type": "status", "msg": "Finding match..."}, username)
        
        # --- MATCHMAKING LOGIC ---
        match_data = await matchmaker.add_to_queue(username)
        
        if match_data["status"] == "MATCH_FOUND":
            player1 = match_data["players"][0]
            player2 = match_data["players"][1]
            game_id = match_data["game_id"]
            
            # Fetch 10 Questions
            questions = await game_utils.get_random_questions(limit=10)
            
            # Game Config
            payload = {
                "type": "GAME_START",
                "game_id": game_id,
                "opponent": "",
                "questions": questions,
                "config": {
                    "question_count": 10,
                    "timer_per_question": 15
                }
            }
            
            # Send to P1
            payload["opponent"] = player2
            await manager.send_personal_message(payload, player1)
            
            # Send to P2
            payload["opponent"] = player1
            await manager.send_personal_message(payload, player2)
            
        else:
            await manager.send_personal_message({"type": "status", "msg": "Waiting for opponent..."}, username)
            
        # --- GAMEPLAY LOOP ---
        while True:
            # Wait for data from Client
            data = await websocket.receive_text()
            message = json.loads(data)
            
# ... Inside the while True loop ...
            if message.get("type") == "SUBMIT_ANSWER":
                q_id = message.get("q_id")
                ans = message.get("answer")
                gid = message.get("game_id")
                opponent_name = message.get("opponent")

                # 1. Fetch the Question to get the correct letter
                async with database.SessionLocal() as session:
                    q_result = await session.execute(
                        select(models.Question).where(models.Question.id == q_id)
                    )
                    question_obj = q_result.scalars().first()
                
                # Safety check
                if not question_obj:
                    continue

                actual_correct_option = question_obj.correct_option
                is_correct = (actual_correct_option == ans)
                
                if is_correct:
                    # Update Score
                    new_score = await game_state.update_score(gid, username, 10)
                    
                    # Notify Self (WITH correct_option)
                    await manager.send_personal_message({
                        "type": "ANSWER_RESULT",
                        "correct": True,
                        "score": new_score,
                        "correct_option": actual_correct_option 
                    }, username)
                    
                    # Notify Opponent
                    if opponent_name:
                        await manager.broadcast_to_user({
                            "type": "OPPONENT_UPDATE",
                            "opponent_score": new_score
                        }, opponent_name)
                else:
                    # Notify Self (WITH correct_option)
                    await manager.send_personal_message({
                        "type": "ANSWER_RESULT",
                        "correct": False,
                        "correct_option": actual_correct_option 
                    }, username)
            # --- NEW LOGIC: INSERT THIS BLOCK HERE ---
            elif message.get("type") == "FINISH_GAME":
                gid = message.get("game_id")
                
                print(f"🏁 User {username} finished game {gid}")
                
                # 1. Mark this user as done in Redis
                # Returns how many people are now finished (1 or 2)
                finished_count = await game_state.mark_finished(gid, username)
                
                # 2. If BOTH players (2) are finished, Save the Match!
                if finished_count >= 2:
                    print(f"💾 Both players finished! Saving Match {gid} to DB...")
                    
                    # A. Fetch Final Scores from Redis
                    final_scores = await game_state.get_game_scores(gid)
                    
                    # B. Save to PostgreSQL
                    await game_utils.save_match(gid, final_scores)
                    
                    # C. Clean up Redis (Free up memory)
                    await game_state.clear_game_data(gid)
                    
                # 3. Acknowledge the client (Optional)
                await manager.send_personal_message({"type": "GAME_OVER_ACK"}, username)
            # --- NEW LOGIC: CANCEL SEARCH ---
            elif message.get("type") == "CANCEL_SEARCH":
                await matchmaker.remove_from_queue(username)
                await manager.send_personal_message({
                    "type": "status", 
                    "msg": "Search Canceled."
                }, username)

    except WebSocketDisconnect:
        manager.disconnect(username)
        # Optional: Handle forfeit logic here