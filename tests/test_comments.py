from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select
from sqlalchemy import and_

from app.models import User, Recommendation, FictionType, Comment
from app.auth import get_password_hash

from .conftest import AuthActions


def test_get_comments(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment_1 = Comment(content='I agree', user=test_user,
                        recommendation=recommendation)
    comment_2 = Comment(content='I agree 2', user=test_user,
                        recommendation=recommendation)
    comment_2.published = comment_2.published + timedelta(minutes=15)
    session.add(comment_1)
    session.add(comment_2)
    session.commit()
    response = client.get(f'/recommendations/{recommendation.id}/comments')
    assert response.status_code == status.HTTP_200_OK
    comments_for_recommendation = session.exec(select(Comment).
                                               where(Comment.recommendation_id == recommendation.id)).all()
    assert len(response.json()) == len(comments_for_recommendation)
    assert response.json()[0]['id'] == comment_1.id
    response = client.get(
        f'/recommendations/{recommendation.id}/comments?by_published_date_descending=false'
    )
    assert len(response.json()) == len(comments_for_recommendation)
    assert response.json()[0]['id'] == comment_1.id
    response = client.get(
        f'/recommendations/{recommendation.id}/comments?by_published_date_descending=true'
    )
    assert len(response.json()) == len(comments_for_recommendation)
    assert response.json()[0]['id'] == comment_2.id
    response = client.get(
        f'/recommendations/{recommendation.id}/comments?offset=1'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['id'] == comment_2.id
    response = client.get(
        f'/recommendations/{recommendation.id}/comments?limit=1'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['id'] == comment_1.id


def test_get_comments_for_nonexistent_recommendation(client: TestClient):
    nonexistent_recommendation_id = 89
    response = client.get(
        f'/recommendations/{nonexistent_recommendation_id}/comments')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_post_comment_for_not_logged_user(client: TestClient):
    response = client.post('/recommendations/78/comments')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_post_comment_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 49
    response = client.post(f'/recommendations/{nonexistent_recommendation_id}/comments',
                           json={'content': 'comment'}, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_post_comment_validate_input(client: TestClient, auth: AuthActions, session: Session):
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
    response = client.post(f'/recommendations/{recommendation.id}/comments',
                           json={'content': None},
                           headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_comment_with_no_data(client: TestClient, auth: AuthActions, session: Session):
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
    response = client.post(f'/recommendations/{recommendation.id}/comments',
                           json={},
                           headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_post_comment_with_no_body(client: TestClient, auth: AuthActions, session: Session):
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
    response = client.post(f'/recommendations/{recommendation.id}/comments',
                           json=None, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_logged_user_posts_comment(client: TestClient, auth: AuthActions, session: Session):
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
    response = client.post(f'/recommendations/{recommendation.id}/comments',
                           json={'content': 'My comment'},
                           headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    comment: Comment = session.exec(select(Comment).where(
        and_(Comment.recommendation_id == recommendation.id,
             Comment.user_id == test_user.id)
    )).first()
    assert comment is not None
    comment_published_date_for_json = str(comment.published).replace(' ', 'T')
    expected_data = {
        'content': comment.content,
        'id': comment.id,
        'user_id': test_user.id,
        'recommendation_id': recommendation.id,
        'published': comment_published_date_for_json,
        'updated': None
    }
    assert response.json() == expected_data


def test_get_comment_for_nonexistent_recommendation(client: TestClient):
    nonexistent_recommendation_id = 99
    response = client.get(
        f'/recommendations/{nonexistent_recommendation_id}/comments/45')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_get_nonexistent_comment_for_recommendation(client: TestClient, session: Session):
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
    nonexistent_comment_id = 87
    response = client.get(
        f'/recommendations/{recommendation.id}/comments/{nonexistent_comment_id}')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Comment with id {nonexistent_comment_id} for recommendation with id {recommendation.id} was not found"
    assert response.json()['detail'] == error_detail


def test_get_comment(client: TestClient, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    response = client.get(
        f'/recommendations/{recommendation.id}/comments/{comment.id}')
    assert response.status_code == status.HTTP_200_OK
    comment_published_date_for_json = str(comment.published).replace(' ', 'T')
    expected_data = {
        'content': comment.content,
        'id': comment.id,
        'user_id': comment.user_id,
        'recommendation_id': comment.recommendation_id,
        'published': comment_published_date_for_json,
        'updated': None
    }
    assert response.json() == expected_data


def test_update_comment_validate_input(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        json={'content': None}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_comment_with_no_data(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        json={}, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_comment_with_no_body(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        json=None, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_logged_user_updates_comment(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        json={'content': 'My updated comment'}, headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    session.refresh(comment)
    assert comment.updated is not None
    comment_published_date_for_json = str(comment.published).replace(' ', 'T')
    comment_updated_date_for_json = str(comment.updated).replace(' ', 'T')
    expected_data = {
        'content': comment.content,
        'id': comment.id,
        'user_id': comment.user_id,
        'recommendation_id': comment.recommendation_id,
        'published': comment_published_date_for_json,
        'updated': comment_updated_date_for_json
    }
    assert response.json() == expected_data


def test_not_logged_user_updates_comment(client: TestClient):
    response = client.put('/recommendations/67/comments/78')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_logged_user_with_no_permission_updates_comment(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    new_user = User(username='new_user', email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.put(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        json={'content': 'My updated comment'}, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'detail' in response.json()
    error_detail = f"User has no permission to update comment with id {comment.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_updates_comment_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 49
    response = client.put(f'/recommendations/{nonexistent_recommendation_id}/comments/89',
                          json={'content': 'Some content'},
                          headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'detail' in response.json()
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_updates_nonexistent_comment(client: TestClient, auth: AuthActions, session: Session):
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
    nonexistent_comment_id = 89
    response = client.put(f'/recommendations/{recommendation.id}/comments/{nonexistent_comment_id}',
                          json={'content': 'Some content'},
                          headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_detail = f"Comment with id {nonexistent_comment_id} for recommendation with id {recommendation.id} was not found"
    assert response.json()['detail'] == error_detail


def test_not_logged_user_deletes_comment(client: TestClient):
    response = client.delete('/recommendations/34/comments/45')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "www-authenticate" in dict(response.headers)
    assert dict(response.headers)['www-authenticate'] == 'Bearer'


def test_logged_user_deletes_comment_for_nonexistent_recommendation(client: TestClient, auth: AuthActions):
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    nonexistent_recommendation_id = 45
    response = client.delete(
        f'/recommendations/{nonexistent_recommendation_id}/comments/90',
        headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_detail = f"Recommendation with id {nonexistent_recommendation_id} was not found"
    assert response.json()['detail'] == error_detail


def test_logged_user_deletes_nonexistent_comment(client: TestClient, auth: AuthActions, session: Session):
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
    nonexistent_comment_id = 89
    response = client.delete(f'/recommendations/{recommendation.id}/comments/{nonexistent_comment_id}',
                             headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_detail = f"Comment with id {nonexistent_comment_id} for recommendation with id {recommendation.id} was not found"
    assert response.json()['detail'] == error_detail


def test_user_without_permission_deletes_comment(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    new_user = User(username='new_user',
                    email='new_user@gmail.com',
                    hashed_password=get_password_hash('34somepassword34'))
    session.add(new_user)
    session.commit()
    token = auth.login_user_for_token(username='new_user',
                                      password='34somepassword34')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete(
        f'/recommendations/{recommendation.id}/comments/{comment.id}',
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'detail' in response.json()
    error_detail = f"User has no permission to delete comment with id {comment.id}"
    assert response.json()['detail'] == error_detail


def test_logged_user_deletes_comment(client: TestClient, auth: AuthActions, session: Session):
    test_user = session.exec(select(User).where(
        User.username == 'test_user')).first()
    fiction_type = FictionType(name='movie', slug='movie')
    recommendation = Recommendation(
        title='Interstellar', short_description='Movie about space',
        opinion='My favorite movie', fiction_type=fiction_type,
        user=test_user
    )
    comment = Comment(content='My comment',
                      user=test_user, recommendation=recommendation)
    session.add(comment)
    session.commit()
    comment_id = comment.id
    token = auth.login_user_for_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete(
        f'/recommendations/{recommendation.id}/comments/{comment_id}',
        headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    comment = session.get(Comment, comment_id)
    assert comment is None
