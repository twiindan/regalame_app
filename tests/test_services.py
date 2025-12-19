from unittest.mock import patch
import pytest
from sqlmodel import select
from services import scrape_metadata, generate_amazon_link, perform_draw
from models import User, Group, GroupMember, GroupExclusion

def test_generate_amazon_link_text():
    link = generate_amazon_link("PlayStation 5")
    assert "PlayStation+5" in link
    assert "tag=" in link

def test_generate_amazon_link_url():
    # Probar que inyecta el tag en una URL existente
    url = "https://www.amazon.es/dp/B08H93ZRLL?ref_=ast_sto_dp"
    link = generate_amazon_link(url)
    assert "tag=" in link
    assert "B08H93ZRLL" in link

@patch("services.requests.get")
def test_scrape_metadata_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html><meta property='og:title' content='Producto Test' /><meta property='og:image' content='http://img.com/foto.jpg' /></html>"
    data = scrape_metadata("http://fakeurl.com")
    assert data["title"] == "Producto Test"
    assert data["image_url"] == "http://img.com/foto.jpg"

def test_perform_draw_with_exclusions(session):
    # Crear 3 usuarios: U1, U2 (pareja), U3 (soltero)
    u1 = User(email="u1@t.com", name="U1", hashed_password="x")
    u2 = User(email="u2@t.com", name="U2", hashed_password="x")
    u3 = User(email="u3@t.com", name="U3", hashed_password="x")
    session.add_all([u1, u2, u3]); session.commit()
    
    g = Group(name="Test Group", code="123", admin_id=u1.id)
    session.add(g); session.commit()
    
    session.add_all([
        GroupMember(group_id=g.id, user_id=u1.id),
        GroupMember(group_id=g.id, user_id=u2.id),
        GroupMember(group_id=g.id, user_id=u3.id)
    ]); session.commit()
    
    # REGLA: U1 NO puede regalar a U2
    # En un grupo de 3, si U1 no regala a U2, solo puede regalar a U3.
    # Por tanto U2 regala a U1 y U3 regala a U2.
    session.add(GroupExclusion(group_id=g.id, giver_id=u1.id, forbidden_giftee_id=u2.id))
    session.commit()
    
    perform_draw(g.id, session)
    
    m1 = session.exec(select(GroupMember).where(GroupMember.group_id == g.id, GroupMember.user_id == u1.id)).first()
    assert m1.giftee_id == u3.id # Obligatorio por el veto a U2