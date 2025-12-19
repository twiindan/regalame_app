import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

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