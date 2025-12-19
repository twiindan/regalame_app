import pytest
from sqlmodel import Session, select
from models import User, Group, GroupMember, Message
from security import get_password_hash

def test_chat_access_and_creation(client, session: Session):
    # Setup: Create 3 users and a group
    pwd_hash = get_password_hash("password123")
    user1 = User(email="u1@test.com", hashed_password=pwd_hash, name="User1")
    user2 = User(email="u2@test.com", hashed_password=pwd_hash, name="User2")
    user3 = User(email="u3@test.com", hashed_password=pwd_hash, name="User3")
    session.add(user1)
    session.add(user2)
    session.add(user3)
    session.commit()
    
    group = Group(name="Chat Group", code="CHAT123", admin_id=user1.id)
    session.add(group)
    session.commit()
    
    # Chain: U1 -> U2 -> U3 -> U1
    m1 = GroupMember(group_id=group.id, user_id=user1.id, giftee_id=user2.id) 
    m2 = GroupMember(group_id=group.id, user_id=user2.id, giftee_id=user3.id)
    m3 = GroupMember(group_id=group.id, user_id=user3.id, giftee_id=user1.id)
    session.add(m1)
    session.add(m2)
    session.add(m3)
    session.commit()

    # Login as User1
    login_resp = client.post("/login", data={"email": "u1@test.com", "password": "password123"})
    assert login_resp.status_code == 200
            
    # 1. Test GET Chat (User1 -> User2)
    # User1 is Santa of User2. User2 is NOT Santa of User1.
    # User1 should see "User2" name and "Estás en modo incógnito".
    response = client.get(f"/group/{group.id}/chat/{user2.id}")
    assert response.status_code == 200
    assert "User2" in response.text 
    assert "Estás en modo incógnito" in response.text 
    assert "Santa Secreto" not in response.text # Should not see this header

    # 2. Test POST Message (User1 -> User2)
    response = client.post(f"/group/{group.id}/chat/{user2.id}", data={"content": "Ho Ho Ho"})
    assert response.status_code == 200
    
    # Verify DB
    msgs = session.exec(select(Message)).all()
    assert len(msgs) == 1
    assert msgs[0].content == "Ho Ho Ho"
    assert msgs[0].sender_id == user1.id
    assert msgs[0].receiver_id == user2.id

    # Logout User1
    client.get("/logout")

    # Login as User2 (The Giftee of User1)
    client.post("/login", data={"email": "u2@test.com", "password": "password123"})
            
    # 3. Test GET Chat (User2 -> User1) - Viewing message from Santa
    # User2 is receiving from User1 (Santa). User2 should NOT see "User1" name, but "Santa Secreto".
    response = client.get(f"/group/{group.id}/chat/{user1.id}")
    assert response.status_code == 200
    assert "Santa Secreto" in response.text
    assert "User1" not in response.text # Should be hidden
    assert "Ho Ho Ho" in response.text

    # 4. Reply
    response = client.post(f"/group/{group.id}/chat/{user1.id}", data={"content": "Thanks Santa!"})
    assert response.status_code == 200
    
    msgs = session.exec(select(Message).order_by(Message.timestamp)).all()
    assert len(msgs) == 2
    assert msgs[1].content == "Thanks Santa!"
