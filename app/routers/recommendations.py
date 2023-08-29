from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Body, Depends, status, HTTPException, Path, Query
from sqlmodel import Session, select
from ..auth import get_current_user
from ..database import get_session
from ..schemas import RecommendationCreate, RecommendationRead, RecommendationUpdate
from ..models import Tag, User, Recommendation, FictionType
from ..crud import get_recommendation_by_id_with_tags_and_fiction_type, get_fiction_type_by_slug,\
    get_all_recommendations, get_recommendations_by_fiction_type, get_recommendation_by_id


router = APIRouter(
    tags=['recommendations']
)


def save_tags(session: Session, tags: [str]) -> list[Tag]:
    tag_objects = []
    for tag in tags:
        tag: str = tag.strip().replace(' ', '-').lower()
        existing_tag = session.exec(
            select(Tag).where(Tag.name == tag)).first()
        if existing_tag:
            tag_objects.append(existing_tag)
        else:
            new_tag = Tag(name=tag)
            # There is no need to save new tags with session.add(), session.commit(),
            # as because tags are related to recommendation, when saving recommendation, all
            # tags will be automatically saved
            tag_objects.append(new_tag)

    return tag_objects


def save_fiction_type(session: Session, fiction_type: str) -> FictionType:
    fiction_type = fiction_type.strip().lower()
    existing_fiction_type_object = session.exec(select(FictionType).
                                                where(FictionType.name == fiction_type)).first()
    if existing_fiction_type_object:
        return existing_fiction_type_object
    else:
        fiction_type_slug = fiction_type.replace(' ', '-')
        new_fiction_type_object = FictionType(name=fiction_type,
                                              slug=fiction_type_slug)
        return new_fiction_type_object


@router.get('/recommendations', response_model=list[RecommendationRead])
async def get_recommendations(*, fiction_type_slug: Annotated[str | None, Query()] = None,
                              offset: Annotated[int | None,
                                                Query(gt=0)] = None,
                              limit: Annotated[int | None, Query(gt=0)] = None,
                              session: Annotated[Session, Depends(get_session)]):
    if not fiction_type_slug:
        recommendations = get_all_recommendations(session=session,
                                                  offset=offset,
                                                  limit=limit)
        return recommendations
    else:
        fiction_type_object = get_fiction_type_by_slug(session=session,
                                                       fiction_type_slug=fiction_type_slug)
        if not fiction_type_object:
            return []
        else:
            recommendations = get_recommendations_by_fiction_type(session=session,
                                                                  fiction_type=fiction_type_object,
                                                                  offset=offset,
                                                                  limit=limit)
            return recommendations


@router.post('/recommendations',
             response_model=RecommendationRead,
             status_code=status.HTTP_201_CREATED)
async def post_recommendation(
    data: Annotated[RecommendationCreate, Body(),],
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    tags = save_tags(session=session, tags=data.tags)
    fiction_type = save_fiction_type(
        session=session, fiction_type=data.fiction_type)
    recommendation = Recommendation(
        title=data.title,
        short_description=data.short_description,
        opinion=data.opinion,
        fiction_type=fiction_type,
        tags=tags,
        user=current_user
    )
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


@router.get('/recommendations/{recommendation_id}',
            response_model=RecommendationRead)
async def get_recommendation(recommendation_id: Annotated[int, Path()],
                             session: Annotated[Session, Depends(get_session)]
                             ):
    recommendation = get_recommendation_by_id_with_tags_and_fiction_type(session=session,
                                                                         recommendation_id=recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Recommendation with id {recommendation_id} was not found'
        )
    return recommendation


@router.patch('/recommendations/{recommendation_id}',
              response_model=RecommendationRead)
async def update_recommendation(recommendation_id: Annotated[int, Path()],
                                session: Annotated[Session, Depends(get_session)],
                                current_user: Annotated[User, Depends(get_current_user)],
                                data: Annotated[RecommendationUpdate, Body()]):
    recommendation = get_recommendation_by_id(session=session,
                                              recommendation_id=recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    if recommendation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User has no permission to update recommendation with id {recommendation_id}"
        )
    data: dict = data.dict(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided"
        )
    new_title = data.get("title")
    new_short_description = data.get("short_description")
    new_opinion = data.get("opinion")
    new_fiction_type = data.get("fiction_type")
    new_tags = data.get("tags")
    if new_title:
        recommendation.title = new_title
    if new_short_description:
        recommendation.short_description = new_short_description
    if new_opinion:
        recommendation.opinion = new_opinion
    if new_fiction_type:
        new_fiction_type = save_fiction_type(session=session,
                                             fiction_type=new_fiction_type)
        recommendation.fiction_type = new_fiction_type
    if new_tags:
        new_tags = save_tags(session=session,
                             tags=new_tags)
        recommendation.tags = new_tags
    recommendation.updated = datetime.utcnow()
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


@router.delete('/recommendations/{recommendation_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               response_model=None)
async def delete_recommendation(recommendation_id: Annotated[int, Path()],
                                session: Annotated[Session, Depends(get_session)],
                                current_user: Annotated[User, Depends(get_current_user)]):
    recommendation = get_recommendation_by_id(session=session,
                                              recommendation_id=recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    if recommendation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User has no permission to delete recommendation with id {recommendation_id}"
        )
    session.delete(recommendation)
    session.commit()
    return None
