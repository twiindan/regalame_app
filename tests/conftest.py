import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from catalog import normalize_text
from main import app, get_session
from models import User
from security import get_password_hash

# Usamos SQLite en memoria con StaticPool para que la misma conexión se use en todo el thread
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    # Crea un usuario por defecto para los tests que requieran auth
    user = User(
        email="test@example.com", 
        name="Test User", 
        hashed_password=get_password_hash("password123")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="auth_client")
def auth_client_fixture(client: TestClient, test_user: User):
    # Simula un cliente ya logueado manipulando la cookie de sesión (la app usa user_id en session)
    # Nota: TestClient maneja cookies, pero necesitamos 'inyectar' la sesión del backend.
    # Dado que usamos SessionMiddleware, lo más fácil en tests de integración es hacer login.
    client.post("/login", data={"email": "test@example.com", "password": "password123"})
    return client

@pytest.fixture(name="catalog_seed")
def catalog_seed_fixture(session: Session):
    """Insert a small, known catalog: 3 products across 2 categories and 2 lists."""
    from datetime import datetime
    from models import Product, ProductList

    def make(asin, title, category, slug, price, image, url, when):
        return Product(
            asin=asin,
            title=title,
            title_normalized=normalize_text(title),
            image_url=image,
            url=url,
            category=category,
            category_slug=slug,
            price_numeric=price,
            price_raw=f"{price} €" if price is not None else "N/A",
            scraped_at=when,
        )

    products = [
        make("A1", "Café molido", "Alimentación y bebidas", "alimentacion-y-bebidas", 10.0,
             "img-a1.jpg", "https://www.amazon.es/dp/A1", datetime(2026, 1, 1)),
        make("A2", "Cafetera express", "Alimentación y bebidas", "alimentacion-y-bebidas", 100.0,
             "img-a2.jpg", "https://www.amazon.es/dp/A2", datetime(2026, 3, 1)),
        make("B1", "Auriculares bluetooth", "Electrónica", "electronica", None,
             "img-b1.jpg", "https://www.amazon.es/dp/B1", datetime(2026, 2, 1)),
    ]
    session.add_all(products)
    session.commit()
    for p in products:
        session.refresh(p)

    session.add_all([
        ProductList(product_id=products[0].id, list_key="bestsellers", rank=1),
        ProductList(product_id=products[1].id, list_key="bestsellers", rank=2),
        ProductList(product_id=products[1].id, list_key="trends", rank=1),
        ProductList(product_id=products[2].id, list_key="trends", rank=2),
    ])
    session.commit()
    return products