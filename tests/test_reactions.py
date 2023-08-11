import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select
from sqlalchemy import and_

from app.models import User, Recommendation, FictionType, Reaction
from app.auth import get_password_hash

from .conftest import AuthActions


def test_get_reactions(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    user_1 = User(username='user1', email='user1@gmail.com',
                  hashed_password=get_password_hash('34somepassword34'))
    user_2 = User(username='user2', email='user2@gmail.com',
                  hashed_password=get_password_hash('34somepassword34'))
    reaction_1 = Reaction(is_positive=True, user=user_1,
                          recommendation=recommendation)
    reaction_2 = Reaction(is_positive=False, user=user_2,
                          recommendation=recommendation)
    session.add(reaction_1)
    session.add(reaction_2)
    session.commit()
    response = client.get(f'/recommendations/{recommendation.id}/reactions')
    assert response.status_code == status.HTTP_200_OK
    reactions_for_recommendation = session.exec(select(Reaction).
                                                where(Reaction.recommendation_id == recommendation.id)).all()
    assert len(response.json()) == len(reactions_for_recommendation)
    assert response.json()[0]['id'] == reaction_1.id
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions?is_positive=true')
    assert response.status_code == status.HTTP_200_OK
    positive_reactions_for_recommendation = session.exec(select(Reaction).where(
        and_(Reaction.recommendation_id == recommendation.id,
             Reaction.is_positive == True)
    )).all()
    assert len(response.json()) == len(positive_reactions_for_recommendation)
    assert response.json()[0]['id'] == reaction_1.id
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions?is_positive=false'
    )
    assert response.status_code == status.HTTP_200_OK
    negative_reactions_for_recommendation = session.exec(select(Reaction).where(
        and_(Reaction.recommendation_id == recommendation.id,
             Reaction.is_positive == False)
    )).all()
    assert len(response.json()) == len(negative_reactions_for_recommendation)
    assert response.json()[0]['id'] == reaction_2.id
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions?offset=1')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['id'] == reaction_2.id
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions?limit=1'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['id'] == reaction_1.id


def test_get_reactions_for_nonexistent_recommendation(client: TestClient):
    nonexistent_recommendation_id = 89
    response = client.get(
        f'/recommendations/{nonexistent_recommendation_id}/reactions'
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_post_reaction_for_not_logged_user(client: TestClient):
    response = client.post('/recommendations/78/reactions')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_post_reaction_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 57
    response = client.post(f'/recommendations/{nonexistent_recommendation_id}/reactions',
                           json={'is_positive': True}, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_post_reaction_validate_input(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post(f'/recommendations/{recommendation.id}/reactions',
                           json={'is_positive': None},
                           headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_reaction_with_no_data(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post(f'/recommendations/{recommendation.id}/reactions',
                           json={}, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_reaction_with_no_body(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post(f'/recommendations/{recommendation.id}/reactions',
                           json=None, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_logged_user_posts_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post(f'/recommendations/{recommendation.id}/reactions',
                           json={'is_positive': True}, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    reaction: Reaction = session.exec(select(Reaction).where(
        and_(Reaction.user_id == test_user.id,
             Reaction.recommendation_id == recommendation.id)
    )).first()
    assert reaction is not None
    expected_data = {'is_positive': reaction.is_positive,
                     'id': reaction.id,
                     'user_id': reaction.user_id,
                     'recommendation_id': reaction.recommendation_id}
    assert response.json() == expected_data


def test_user_with_reaction_posts_new_reactions(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.post(
        f'/recommendations/{recommendation.id}/reactions',
        json={'is_positive': True}, headers=headers
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert 'detail' in response.json()
    error_detail = f"User already has a reaction for recommendation with id {recommendation.id}, creating another one will create conflict"
    assert response.json()['detail'] == error_detail
    reactions_by_user_for_recommendation = session.exec(select(Reaction).where(
        and_(Reaction.user_id == test_user.id,
             Reaction.recommendation_id == recommendation.id)
    )).all()
    assert len(reactions_by_user_for_recommendation) == 1


def test_get_reaction_for_nonexistent_recommendation(client: TestClient):
    nonexistent_recommendation_id = 48
    response = client.get(
        f'/recommendations/{nonexistent_recommendation_id}/reactions/34')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_get_nonexistent_reaction_for_recommendation(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    nonexistent_reaction_id = 98
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions/{nonexistent_reaction_id}')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Reaction with id {nonexistent_reaction_id} for recommendation with id {recommendation.id} was not found"
    assert response.json()['detail'] == error_detail


def test_get_reaction(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user,
                        recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    response = client.get(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}')
    assert response.status_code == status.HTTP_200_OK
    expected_data = {
        'is_positive': reaction.is_positive,
        'id': reaction.id,
        'user_id': reaction.user_id,
        'recommendation_id': reaction.recommendation_id
    }
    assert response.json() == expected_data


def test_update_reaction_validate_input(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user,
                        recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        json={'is_positive': None}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_reaction_with_no_data(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        json={}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_reaction_with_no_body(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        json=None, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_logged_user_updates_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        json={'is_positive': False}, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    reaction_by_user_for_recommendation: Reaction = session.exec(select(Reaction).where(
        and_(Reaction.recommendation_id == recommendation.id,
             Reaction.user_id == test_user.id)
    )).first()
    assert reaction_by_user_for_recommendation.is_positive == False
    expected_data = {
        'is_positive': reaction_by_user_for_recommendation.is_positive,
        'id': reaction_by_user_for_recommendation.id,
        'user_id': reaction_by_user_for_recommendation.user_id,
        'recommendation_id': reaction_by_user_for_recommendation.recommendation_id
    }
    assert response.json() == expected_data


def test_not_logged_user_updates_comment(client: TestClient):
    response = client.put('/recommendations/94/reactions/75')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_logged_user_without_permission_updates_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    new_user = User(username='new_user',
                    email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        json={'is_positive': False}, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'detail' in response.json()
    error_detail = f"User has no permission to update reaction with id {reaction.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_updates_reaction_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 99
    response = client.put(
        f'/recommendations/{nonexistent_recommendation_id}/reactions/89',
        json={'is_positive': True}, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_updates_nonexistent_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_reaction_id = 65
    response = client.put(
        f'/recommendations/{recommendation.id}/reactions/{nonexistent_reaction_id}',
        json={'is_positive': True}, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Reaction with id {nonexistent_reaction_id} for recommendation with id {recommendation.id} was not found"


def test_not_logged_user_deletes_reaction(client: TestClient):
    response = client.delete(
        '/recommendations/78/reactions/56'
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_logged_user_deletes_comment_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 98
    response = client.delete(
        f'/recommendations/{nonexistent_recommendation_id}/reactions/89',
        headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_deletes_nonexistent_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    session.add(recommendation)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_reaction_id = 98
    response = client.delete(
        f'/recommendations/{recommendation.id}/reactions/{nonexistent_reaction_id}',
        headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Reaction with id {nonexistent_reaction_id} for recommendation with id {recommendation.id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_without_permission_deletes_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    new_user = User(username='new_user', email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'detail' in response.json()
    error_detail = f"User has no permission to delete reaction with id {reaction.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_deletes_reaction(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    reaction = Reaction(user=test_user, recommendation=recommendation,
                        is_positive=True)
    session.add(reaction)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    reaction_id = reaction.id
    response = client.delete(
        f'/recommendations/{recommendation.id}/reactions/{reaction.id}',
        headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    reaction_by_user_for_recommendation = session.get(Reaction, reaction_id)
    assert reaction_by_user_for_recommendation is None
