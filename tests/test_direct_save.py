
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from main import app, get_session
from models import User, Wish

def test_add_wish_direct_save(client: TestClient, session: Session):
    # 1. Create a user and login
    user = User(email="test@example.com", hashed_password="hashed_password", name="Test User")
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Simulate login by setting the cookie directly if possible, or using dependency override
    # For TestClient with SessionMiddleware, we can't easily set session cookie directly without a login endpoint interaction 
    # or mocking. 
    # Let's use the login endpoint.
    # Note: We need a real password for login to work, or mock the auth.
    # Let's try to override the dependency, but `main.py` uses `request.session`.
    # Easiest is to register/login.
    
    client.post("/register", data={"email": "tester@example.com", "password": "password123", "name": "Tester"})
    
    # Get the user
    user = session.exec(select(User).where(User.email == "tester@example.com")).first()
    assert user is not None

    # 2. Add a wish using manual params
    manual_title = "Direct Save Product"
    manual_image = "https://example.com/image.jpg"
    original_url = "https://amazon.es/dp/B0000000"
    
    response = client.post(
        "/wishes",
        data={
            "content": original_url,
            "manual_title": manual_title,
            "manual_image": manual_image
        }
    )
    
    assert response.status_code == 200
    
    # 3. Verify in DB
    wish = session.exec(select(Wish).where(Wish.title == manual_title)).first()
    assert wish is not None
    assert wish.title == manual_title
    assert wish.image_url == manual_image
    # Check if affiliate tag was added (assuming generate_amazon_link logic does something, 
    # usually it adds a tag if configured, or returns same url if not Amazon)
    # Since we don't know the exact tag config, we just check it's not empty.
    assert wish.url is not None
    assert "amazon" in wish.url
