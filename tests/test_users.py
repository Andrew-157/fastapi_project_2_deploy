import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select

from app.models import User
from app.auth import get_password_hash

from .conftest import AuthActions


def test_register(client: TestClient, session: Session):
    response = client.post(
        '/auth/register',
        json={"username": "user1",
              "email": "user1@gmail.com",
              "password": "34somepassword34"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = session.exec(select(User).where(User.username == "user1")).first()
    assert user is not None
    expected_data = {'username': user.username,
                     'email': user.email,
                     'id': user.id}
    assert response.json() == expected_data


@pytest.mark.parametrize(('username', 'email', 'password'),
                         ((None, 'new_email@gmail.com', '34somepassword34'),
                          ('new_user', None, '34somepassword34'),
                          ('new_user', 'new_user@gmail.com', None),
                          ('new_user', 'invalid', '34somepassword34'),
                          ('shor', 'new_user@gmail.com', '34somepassword34'),
                          ('new_user', 'new_email@gmail.com', 'short')))
def test_register_with_invalid_values(client: TestClient, username, email, password):
    response = client.post('/auth/register',
                           json={'username': username,
                                 'email': email,
                                 'password': password})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(('username', 'email', 'password', 'detail'),
                         (('test_user', 'new_email@gmail.com', '34somepassword34', 'Duplicate username'),
                          ('new_username', 'test_user@gmail.com', '34somepassword34', 'Duplicate email')))
def test_register_with_duplicate_values(client: TestClient, username, email, password, detail):
    response = client.post('/auth/register',
                           json={'username': username,
                                 'email': email,
                                 'password': password})
    assert response.status_code == status.HTTP_409_CONFLICT
    assert 'detail' in response.json()
    assert response.json() == {'detail': detail}


def test_login_with_invalid_data(client: TestClient):
    response = client.post('/auth/token',
                           data={'username': 'no_one',
                                 'password': 'nothing'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_login(client: TestClient, session: Session):
    new_user = User(username='new_user',
                    email='new_email@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    response = client.post('/auth/token',
                           data={'username': 'new_user',
                                 'password': '34somepassword34'})
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_read_users_me(client: TestClient, auth: AuthActions, session: Session):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/auth/users/me', headers=headers)
    assert response.status_code == status.HTTP_200_OK
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    expected_data = {'username': test_user.username,
                     'email': test_user.email,
                     'id': test_user.id}
    assert response.json() == expected_data


def test_read_users_me_for_not_logged_user(client: TestClient):
    response = client.get('/auth/users/me')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


@pytest.mark.parametrize(
    ('username', 'email'),
    ((None, 'invalid'),
     ('shor', None),
     ('shor', 'invalid')))
def test_update_user_with_invalid_data(client: TestClient, auth: AuthActions, username, email):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me',
                            json={'username': username,
                                  'email': email}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_user_with_duplicate_username(client: TestClient, auth: AuthActions, session: Session):
    new_user = User(username='new_user',
                    email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username=new_user.username,
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me',
                            json={'username': 'test_user'}, headers=headers)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'Duplicate username'


def test_update_user_with_duplicate_email(client: TestClient, auth: AuthActions, session: Session):
    new_user = User(username='new_user',
                    email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username=new_user.username,
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me',
                            json={'email': 'test_user@gmail.com'}, headers=headers)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'Duplicate email'


def test_update_user_with_no_data(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me', json={},
                            headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'No data provided'


def test_update_user_username(client: TestClient, auth: AuthActions, session: Session):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me',
                            json={'username': 'test_user_1'},
                            headers=headers)
    assert response.status_code == status.HTTP_200_OK
    test_user = session.exec(select(User).where(
        User.email == 'test_user@gmail.com')).first()
    assert test_user.username == 'test_user_1'
    expected_data = {'username': test_user.username,
                     'email': test_user.email,
                     'id': test_user.id}
    assert response.json() == expected_data


def test_update_user_email(client: TestClient, auth: AuthActions, session: Session):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch('/auth/users/me',
                            json={'email': 'test_user_1@gmail.com'},
                            headers=headers)
    assert response.status_code == status.HTTP_200_OK
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    assert test_user.email == 'test_user_1@gmail.com'
    expected_data = {'username': test_user.username,
                     'email': test_user.email,
                     'id': test_user.id}
    assert response.json() == expected_data


def test_update_user_for_not_logged_user(client: TestClient):
    response = client.patch('/auth/users/me')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'
