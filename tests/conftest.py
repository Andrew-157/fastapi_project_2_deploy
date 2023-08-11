import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import User
from app.auth import get_password_hash


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine('sqlite:///:memory:',
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        test_user = User(username='test_user',
                         email='test_user@gmail.com',
                         hashed_password=get_password_hash('34somepassword34'))
        session.add(test_user)
        session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class AuthActions(object):
    def __init__(self, client: TestClient):
        self._client = client

    def login_user_for_token(self,
                             username="test_user",
                             password='34somepassword34'):
        response = self._client.post(
            '/auth/token', data={'username': username,
                                 'password': password})
        token = response.json()["access_token"]
        return token


@pytest.fixture
def auth(client: TestClient):
    return AuthActions(client)
