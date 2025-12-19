from fastapi.testclient import TestClient
from sqlmodel import Session, select
from models import Group, Wish, User
from datetime import date

def test_create_group_with_logistics(auth_client: TestClient, session: Session):
    response = auth_client.post("/create-group", data={
        "name": "Grupo Logística",
        "emails": "",
        "budget": "20€",
        "event_date": "2024-12-25"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "20€" in response.text
    
    group = session.exec(select(Group).where(Group.name == "Grupo Logística")).first()
    assert group.budget == "20€"
    assert group.event_date == date(2024, 12, 25)

def test_delete_wish(auth_client: TestClient, session: Session, test_user: User):
    # 1. Crear deseo
    wish = Wish(user_id=test_user.id, title="Para borrar")
    session.add(wish); session.commit()
    
    # 2. Borrarlo
    response = auth_client.delete(f"/wishes/{wish.id}")
    assert response.status_code == 200
    
    # 3. Verificar que no existe
    session.expire_all()
    deleted_wish = session.get(Wish, wish.id)
    assert deleted_wish is None

def test_seo_endpoints(client: TestClient):
    # Robots.txt
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Disallow: /group/" in resp.text
    
    # Sitemap
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "<loc>" in resp.text