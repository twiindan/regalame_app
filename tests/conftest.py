from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
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


def pytest_addoption(parser):
    parser.addoption(
        "--editorial-update-baselines",
        action="store_true",
        default=False,
        help=(
            "Regenerate tests/baselines/editorial_off_<surface>.html golden "
            "snapshots. Only run this after an intentional pre-change behavior "
            "change; review the resulting diff."
        ),
    )


@pytest.fixture(name="editorial_update_baselines")
def editorial_update_baselines_fixture(request):
    """True when the suite was launched with --editorial-update-baselines."""
    return request.config.getoption("--editorial-update-baselines")


@pytest.fixture(name="sql_statements")
def sql_statements_fixture():
    """Capture every SQL statement executed on the shared test engine.

    Used by the shadow-mode structural proof (T1): under ``off`` no statement
    may reference the editorial tables. The listener is attached just for the
    requesting test and removed afterwards so other tests stay untouched.
    """
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.fixture(name="seed_editorial")
def seed_editorial_fixture(session: Session):
    """Insert an ``EditorialDecision`` row for a seeded product.

    Defaults to an AI-produced decision (``state`` can be ``None`` for a
    manual-only row). The visibility predicates only read the state/context
    columns, so the fingerprint is a placeholder.
    """
    from curation import EDITORIAL_POLICY_VERSION
    from models import EditorialDecision

    def seed(product, state, context=None, *, manual_state=None, manual_context=None,
             model_id="qwen3.6", policy_version=EDITORIAL_POLICY_VERSION):
        decision = EditorialDecision(
            product_id=product.id,
            state=state,
            context=context,
            reason=f"{state or manual_state} decision",
            model_id=model_id,
            policy_version=policy_version,
            input_fingerprint="seed",
            manual_state=manual_state,
            manual_context=manual_context,
            manual_updated_at=datetime(2026, 1, 1) if manual_state is not None else None,
        )
        session.add(decision)
        session.commit()
        return decision

    return seed

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