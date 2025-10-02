from fastapi import FastAPI
from pydantic import BaseModel
import database
import uvicorn
api = FastAPI()

# ---- Request Models ----
class UserCreate(BaseModel):
    email: str
    name: str

class MessageCreate(BaseModel):
    sender_id: str
    recipients: list[str]
    subject: str
    content: str

class MarkAsRead(BaseModel):
    recipient_id: str

    
@api.get("/")
def root():
    return {"message": "API is running"}


# ---- User APIs ----
@api.post("/users/")
def create_user(user: UserCreate):
    """Create new user"""
    return database.create_user(email=user.email, name=user.name)

@api.get("/users/{email}")
def get_user_by_email(email: str):
    """Get user by email"""
    return database.get_user_by_email(email=email)

@api.get("/users/")
def get_all_users():
    """Retrieve all users"""
    return database.get_all_users()


# ---- Message APIs ----
@api.post("/messages/")
def send_message(msg: MessageCreate):
    """Send a message to one or more recipients"""
    return database.send_message(
        sender_id=msg.sender_id,
        recipients=msg.recipients,
        subject=msg.subject,
        content=msg.content
    )

@api.get("/messages/sent/{sender_id}")
def get_all_sent_message(sender_id: str):
    """View all messages sent by a user"""
    return database.get_all_sent_message(sender_id=sender_id)

@api.get("/messages/inbox/{user_id}")
def view_inbox(user_id: str):
    """View inbox messages of a user"""
    return database.view_inbox(user_id=user_id)

@api.get("/messages/unread/{recipient_id}")
def get_unread_message(recipient_id: str):
    """View unread messages for a recipient"""
    return database.get_unread_message(recipient_id=recipient_id)

@api.get("/messages/{message_id}/recipients")
def get_message_with_recipients(message_id: str):
    """View a message with all its recipients"""
    return database.get_message_with_recipients(message_id=message_id)

@api.post("/messages/{message_id}/read")
def mark_as_read(message_id: str, body: MarkAsRead):
    """Mark a message as read for a recipient"""
    return database.mark_as_read(message_id=message_id, recipient_id=body.recipient_id)

if __name__ == "__main__":
    uvicorn.run("api:api", host="192.168.100.6", port=8000, reload=True)
