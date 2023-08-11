import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select


from app.models import User, Recommendation, FictionType, Tag
from app.auth import get_password_hash


from .conftest import AuthActions


def test_get_recommendations(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type_1 = FictionType(name='movie', slug='movie')
    fiction_type_2 = FictionType(name='music', slug='music')
    recommendation_1 = Recommendation(title='Pulp Fiction',
                                      short_description='Cool crime film',
                                      opinion='I like it',
                                      fiction_type=fiction_type_1,
                                      user=test_user)
    recommendation_2 = Recommendation(title='Interstellar',
                                      short_description='Movie about space',
                                      opinion='My favorite movie',
                                      fiction_type=fiction_type_1,
                                      user=test_user)
    recommendation_3 = Recommendation(title='Hero',
                                      short_description='Song by Skillet',
                                      opinion='Amazing song',
                                      fiction_type=fiction_type_2,
                                      user=test_user)
    recommendation_4 = Recommendation(title='One',
                                      short_description='Song by Metallica',
                                      opinion='I love this song',
                                      fiction_type=fiction_type_2,
                                      user=test_user)
    session.add(recommendation_1)
    session.add(recommendation_2)
    session.add(recommendation_3)
    session.add(recommendation_4)
    session.commit()
    response = client.get('/recommendations')
    recommendations = session.exec(select(Recommendation)).all()
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(recommendations)
    recommendations_with_fiction_type_1 = session.exec(select(Recommendation).
                                                       where(Recommendation.fiction_type_id == fiction_type_1.id)).all()
    response = client.get(
        f'/recommendations?fiction_type_slug={fiction_type_1.slug}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(recommendations_with_fiction_type_1)
    recommendations_with_fiction_type_2 = session.exec(select(Recommendation).
                                                       where(Recommendation.fiction_type_id == fiction_type_2.id)).all()
    response = client.get(
        f'/recommendations?fiction_type_slug={fiction_type_2.slug}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(recommendations_with_fiction_type_2)
    response = client.get('/recommendations?fiction_type_slug=guiopoijhg')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = client.get('/recommendations?offset=1')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['title'] == recommendation_2.title
    response = client.get('/recommendations?limit=3')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[-1]['title'] == recommendation_3.title


@pytest.mark.parametrize(
    ('title', 'short_description', 'opinion', 'fiction_type', 'tags'),
    (
        (None, 'Short description', 'My opinion', 'fiction', ['tag']),
        ('Some title', None, 'My opinion', 'fiction', ['tag']),
        ('Some title', 'Short description', None, 'fiction', ['tag']),
        ('Some title', 'Short description', 'My opinion', 'fg', ['tag']),
        ('Some title', 'Short description', 'My opinion', 'fg', []),
        ('Some title', 'Short description', 'My opinion', 'fg', None)
    )
)
def test_post_recommendation_validate_input(client: TestClient, auth: AuthActions,
                                            title, short_description, opinion,
                                            fiction_type, tags):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post('/recommendations', json={'title': title,
                                                     'short_description': short_description,
                                                     'opinion': opinion,
                                                     'fiction_type': fiction_type,
                                                     'tags': tags}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_recommendation_with_no_data(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post('/recommendations', json={}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_recommendation_with_no_body(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post('/recommendations', json=None, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_recommendation(client: TestClient, auth: AuthActions, session: Session):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post('/recommendations', json={
        'title': 'Interstellar',
        'short_description': 'Movie about space',
        'opinion': 'My favorite movie',
        'fiction_type': 'movie',
        'tags': ['sci-fy', 'space']}, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    recommendation = session.exec(select(Recommendation).
                                  where(Recommendation.title == 'Interstellar')).first()
    assert recommendation is not None
    fiction_type = session.exec(select(FictionType).where(
        FictionType.name == 'movie')).first()
    assert fiction_type is not None
    tag_1 = session.exec(select(Tag).where(Tag.name == 'sci-fy')).first()
    assert tag_1 is not None
    tag_2 = session.exec(select(Tag).where(Tag.name == 'space')).first()
    assert tag_2 is not None
    recommendation_published_date_for_json = str(
        recommendation.published).replace(' ', 'T')
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    expected_data = {'title': recommendation.title,
                     'short_description': recommendation.short_description,
                     'opinion': recommendation.opinion,
                     'id': recommendation.id,
                     'user_id': test_user.id,
                     'published': recommendation_published_date_for_json,
                     'updated': None,
                     'fiction_type': {
                         'name': fiction_type.name,
                         'slug': fiction_type.slug,
                         'id': fiction_type.id
                     },
                     'tags': [
                         {'name': tag_1.name,
                          'id': tag_1.id},
                         {'name': tag_2.name,
                          'id': tag_2.id}
                     ]
                     }
    assert response.json() == expected_data


def test_post_recommendation_for_not_logged_user(client: TestClient):
    response = client.post('/recommendations')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_get_recommendation(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type)
    session.add(recommendation)
    session.commit()
    response = client.get(f'/recommendations/{recommendation.id}')
    assert response.status_code == status.HTTP_200_OK
    recommendation_published_date_for_json = str(
        recommendation.published).replace(' ', 'T')
    expected_data = {'title': recommendation.title,
                     'short_description': recommendation.short_description,
                     'opinion': recommendation.opinion,
                     'id': recommendation.id,
                     'user_id': test_user.id,
                     'published': recommendation_published_date_for_json,
                     'updated': None,
                     'fiction_type': {
                         'name': fiction_type.name,
                         'slug': fiction_type.slug,
                         'id': fiction_type.id
                     },
                     'tags': []
                     }
    assert response.json() == expected_data


def test_get_nonexistent_recommendation(client: TestClient):
    response = client.get(f'/recommendations/{789}')
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(('fiction_type', 'tags'),
                         (
    ('fg', ['tag']),
    ('movie', 'not list'),
    ('movie', [])
))
def test_update_recommendation_validate_input(client: TestClient, auth: AuthActions, session: Session,
                                              fiction_type, tags):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type_obj = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type_obj)
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch(f'/recommendations/{recommendation.id}',
                            json={'fiction_type': fiction_type,
                                  'tags': tags}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_recommendation_with_no_data(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type_obj = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type_obj)
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch(f'/recommendations/{recommendation.id}',
                            json={}, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'detail' in response.json()
    error_detail = "No data provided"
    assert response.json()['detail'] == error_detail


def test_update_recommendation_with_no_body(client: TestClient, auth: AuthActions, session:  Session):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch(f'/recommendations/89',
                            json=None, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_not_logged_user_updates_recommendation(client: TestClient):
    response = client.patch('/recommendations/78')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logged_user_updates_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 78
    response = client.patch(
        f'/recommendations/{nonexistent_recommendation_id}', json={},
        headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f'Recommendation with id {nonexistent_recommendation_id} was not found'
    assert response.json()['detail'] == error_detail


def test_logged_user_without_permission_updates_recommendation(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type)
    session.add(recommendation)
    new_user = User(username='new_user',
                    email='new_email@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch(f'/recommendations/{recommendation.id}',
                            json={'tags': ['tag']}, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'detail' in response.json()
    error_detail = f"User has no permission to update recommendation with id {recommendation.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_updates_recommendation(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type)
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.patch(f'/recommendations/{recommendation.id}',
                            json={'tags': ['sci-fi']}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    tag = session.exec(select(Tag).where(Tag.name == 'sci-fi')).first()
    assert tag is not None
    session.refresh(recommendation)
    assert recommendation.updated is not None
    recommendation_published_date_for_json = str(
        recommendation.published).replace(' ', 'T')
    recommendation_updated_date_for_json = str(
        recommendation.updated).replace(' ', 'T')
    expected_data = {'title': recommendation.title,
                     'short_description': recommendation.short_description,
                     'opinion': recommendation.opinion,
                     'id': recommendation.id,
                     'user_id': test_user.id,
                     'published': recommendation_published_date_for_json,
                     'updated': recommendation_updated_date_for_json,
                     'fiction_type': {
                         'name': fiction_type.name,
                         'slug': fiction_type.slug,
                         'id': fiction_type.id
                     },
                     'tags': [
                         {'name': tag.name,
                          'id': tag.id}
                     ]
                     }
    assert response.json() == expected_data


def test_not_logged_user_deletes_recommendation(client: TestClient):
    response = client.delete('/recommendations/89')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_logged_user_deletes_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 23
    response = client.delete(
        f'/recommendations/{nonexistent_recommendation_id}', headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_without_permission_deletes_recommendation(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type)
    session.add(recommendation)
    new_user = User(username='new_user',
                    email='new_email@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete(
        f'/recommendations/{recommendation.id}', headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error_detail = f"User has no permission to delete recommendation with id {recommendation.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_deletes_recommendation(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).
                             where(User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(title='Interstellar',
                                    short_description='Movie about space',
                                    opinion='My favorite movie',
                                    user=test_user,
                                    fiction_type=fiction_type)
    session.add(recommendation)
    session.commit()
    recommendation_id = recommendation.id
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete(
        f'/recommendations/{recommendation_id}', headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    recommendation = session.get(Recommendation, recommendation_id)
    assert recommendation is None
