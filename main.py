import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from cli import handle_query
import config

app = FastAPI()

DATABASE_URL = "sqlite:///./db.sqlite3"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    contact_record = Column(String, unique=True)
    chat_type = Column(String)
    type = Column(String)

class TextChat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    chat_content = Column(Text)
    client = relationship("Client", back_populates="chats")
    isReply = Column(Boolean, default=False)


Client.chats = relationship("TextChat", order_by=TextChat.id, back_populates="client")


@app.on_event("startup")
async def startup_event():
    if not os.path.exists("db.sqlite3"):
        print("Database not found. Creating new database.")
        open("db.sqlite3", "w").close()
    try:
        conn = engine.connect()
        print("Database connected.")
        Base.metadata.create_all(bind=engine)
        print("Tables created.")
    except Exception as e:
        print("Database connection failed.")
        print(e)
        raise e
    finally:
        conn.close()

@app.get("/api/v1")
def read_root():
    return {
        "app": "Call Center - API",
        "version": "1.0.0",
        "author": "One More Day...",
        "description": "An API for handling a call center phonecall",
    }

@app.get("/api/v1/health")
def read_health():
    return {
        "status": "healthy",
        "message": "The API is healthy and running.",
    }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication dependency
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token != config.API_KEY and token != "test_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

@app.post("/api/v1/chat/")
def add_phone_chat(
    contact_record: str,
    chat_content: str,
    db: Session = Depends(get_db),
    token: bool = Depends(verify_token)
):
    client = db.query(Client).filter(Client.contact_record == contact_record, Client.chat_type == "call").first()
    if not client:
        client = Client(chat_type="call", contact_record=contact_record)
        db.add(client)
        db.commit()
        db.refresh(client)
    
    phone_chat = TextChat(client_id=client.id, chat_content=chat_content)
    db.add(phone_chat)
    db.commit()
    db.refresh(phone_chat)
    
    chat_history = db.query(TextChat).filter(TextChat.client_id == client.id).order_by(TextChat.id.desc()).all()
    chat_history = [{"role": "user", "content": chat.chat_content} for chat in chat_history]
    chat_history = [chat["content"] for chat in chat_history]

    # use ai model to generate response
    response, _ = handle_query(chat_content, chat_history, "call")

    if not isinstance(response, str):
        response = str(response)

    # save the response to the database
    phone_reply = TextChat(client_id=client.id, chat_content=response, isReply=True)
    db.add(phone_reply)
    db.commit()
    db.refresh(phone_reply)

    return phone_reply

# Endpoint to reset all chats of a client and type.
@app.delete("/api/v1/chat/")
def delete_phone_chat(
    contact_record: str,
    db: Session = Depends(get_db),
    token: bool = Depends(verify_token)
):
    client = db.query(Client).filter(Client.contact_record == contact_record, Client.chat_type == "call").first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    db.query(TextChat).filter(TextChat.client_id == client.id).delete()
    db.commit()
    return {"message": "Chats deleted successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)