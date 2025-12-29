import pytest
from sqlmodel import select
from models import User, Friendship

def test_add_friend_success(auth_client, session, test_user):
    # Create another user
    friend_email = "friend@example.com"
    friend = User(email=friend_email, name="Friend", hashed_password="pwd")
    session.add(friend)
    session.commit()
    session.refresh(friend)
    
    response = auth_client.post("/friends", data={"email": friend_email})
    assert response.status_code == 200
    assert "Friend" in response.text
    
    # Check DB
    friendship = session.exec(select(Friendship).where(Friendship.user_id == test_user.id)).first()
    assert friendship is not None
    assert friendship.friend_id == friend.id

def test_add_friend_self(auth_client, test_user):
    response = auth_client.post("/friends", data={"email": test_user.email})
    assert response.status_code == 200
    assert "No puedes añadirte a ti mismo" in response.text

def test_add_friend_not_found(auth_client):
    response = auth_client.post("/friends", data={"email": "ghost@example.com"})
    assert response.status_code == 200
    assert "Usuario no encontrado" in response.text

def test_add_friend_duplicate(auth_client, session, test_user):
    # Create another user
    friend_email = "friend@example.com"
    friend = User(email=friend_email, name="Friend", hashed_password="pwd")
    session.add(friend)
    session.commit()
    session.refresh(friend)
    
    # Add once
    auth_client.post("/friends", data={"email": friend_email})
    
    # Add again
    response = auth_client.post("/friends", data={"email": friend_email})
    assert response.status_code == 200
    assert "Ya está en tu lista" in response.text

def test_remove_friend(auth_client, session, test_user):
    # Create another user
    friend_email = "friend@example.com"
    friend = User(email=friend_email, name="Friend", hashed_password="pwd")
    session.add(friend)
    session.commit()
    session.refresh(friend)
    
    # Add friend manually
    fs = Friendship(user_id=test_user.id, friend_id=friend.id)
    session.add(fs)
    session.commit()
    
    # Remove
    response = auth_client.delete(f"/friends/{friend.id}")
    assert response.status_code == 200
    
    # Check DB
    friendship = session.exec(select(Friendship).where(Friendship.user_id == test_user.id)).first()
    assert friendship is None
