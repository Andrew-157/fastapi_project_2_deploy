from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Body, Depends, status, HTTPException, Path, Query
from sqlmodel import Session, select

from ..auth import get_current_user
from ..database import get_session
from ..schemas import ReactionCreate, ReactionRead, ReactionUpdate
from ..models import User, Reaction
from ..crud import get_reaction_by_recommendation_id_and_user_id, get_recommendation_by_id,\
    get_all_reactions_for_recommendation, get_reaction_by_id_and_recommendation_id


router = APIRouter(
    tags=['reactions']
)


@router.get('/recommendations/{recommendation_id}/reactions',
            response_model=list[ReactionRead])
async def get_reactions(*,
                        recommendation_id: Annotated[int, Path()],
                        is_positive: Annotated[bool | None, Query()] = None,
                        session: Annotated[Session, Depends(get_session)],
                        offset: Annotated[int | None, Query(gt=0)] = None,
                        limit: Annotated[int | None, Query(gt=0)] = None
                        ):
    recommendation = get_recommendation_by_id(session=session,
                                              recommendation_id=recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    reactions = get_all_reactions_for_recommendation(
        session=session, recommendation_id=recommendation_id,
        is_positive=is_positive, offset=offset, limit=limit
    )
    return reactions


@router.post('/recommendations/{recommendation_id}/reactions',
             response_model=ReactionRead,
             status_code=status.HTTP_201_CREATED)
async def post_reaction(
    recommendation_id: Annotated[int, Path()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    data: Annotated[ReactionCreate, Body()]
):
    recommendation = get_recommendation_by_id(session=session,
                                              recommendation_id=recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    existing_reaction = get_reaction_by_recommendation_id_and_user_id(
        session=session,
        recommendation_id=recommendation.id,
        user_id=current_user.id
    )
    if existing_reaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has a reaction for recommendation with id {recommendation_id}, creating another one will create conflict"
        )

    new_reaction = Reaction(
        is_positive=data.is_positive,
        recommendation_id=recommendation.id,
        user_id=current_user.id
    )
    session.add(new_reaction)
    session.commit()
    session.refresh(new_reaction)
    return new_reaction


@router.get('/recommendations/{recommendation_id}/reactions/{reaction_id}',
            response_model=ReactionRead)
async def get_reaction(
    recommendation_id: Annotated[int, Path()],
    reaction_id: Annotated[int, Path()],
    session: Annotated[Session, Depends(get_session)]
):
    recommendation = get_recommendation_by_id(
        session=session, recommendation_id=recommendation_id
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    reaction = get_reaction_by_id_and_recommendation_id(
        session=session, recommendation_id=recommendation_id,
        reaction_id=reaction_id
    )
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reaction with id {reaction_id} for recommendation with id {recommendation_id} was not found"
        )
    return reaction


@router.put('/recommendations/{recommendation_id}/reactions/{reaction_id}',
            response_model=ReactionRead)
async def update_reaction(
    recommendation_id: Annotated[int, Path()],
    reaction_id: Annotated[int, Path()],
    session: Annotated[Session, Depends(get_session)],
    data: Annotated[ReactionUpdate, Body()],
    current_user: Annotated[User, Depends(get_current_user)]
):
    recommendation = get_recommendation_by_id(
        session=session,
        recommendation_id=recommendation_id
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    reaction = get_reaction_by_id_and_recommendation_id(
        session=session, recommendation_id=recommendation_id,
        reaction_id=reaction_id
    )
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reaction with id {reaction_id} for recommendation with id {recommendation_id} was not found"
        )
    if reaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User has no permission to update reaction with id {reaction_id}"
        )
    data: dict = data.dict()
    new_is_positive = data.get("is_positive")
    reaction.is_positive = new_is_positive
    session.add(reaction)
    session.commit()
    session.refresh(reaction)
    return reaction


@router.delete('/recommendations/{recommendation_id}/reactions/{reaction_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               response_model=None)
async def delete_reaction(
    recommendation_id: Annotated[int, Path()],
    reaction_id: Annotated[int, Path()],
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    recommendation = get_recommendation_by_id(
        session=session, recommendation_id=recommendation_id
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id {recommendation_id} was not found"
        )
    reaction = get_reaction_by_id_and_recommendation_id(
        session=session, recommendation_id=recommendation_id,
        reaction_id=reaction_id
    )
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reaction with id {reaction_id} for recommendation with id {recommendation_id} was not found"
        )
    if reaction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User has no permission to delete reaction with id {reaction_id}"
        )
    session.delete(reaction)
    session.commit()
    return None
