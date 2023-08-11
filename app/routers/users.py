from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Body, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..auth import create_access_token, get_current_user, authenticate_user, Token,\
    ACCESS_TOKEN_EXPIRES_HOURS, get_password_hash
from ..database import get_session
from ..schemas import UserCreate, UserRead, UserUpdate
from ..models import User
from ..crud import get_user_with_username, get_user_with_email


router = APIRouter(
    tags=['users'],
    prefix='/auth'
)


@router.post("/register",
             response_model=UserRead,
             status_code=status.HTTP_201_CREATED)
async def register(*, session: Annotated[Session, Depends(get_session)],
                   data: Annotated[UserCreate, Body()]):
    if get_user_with_username(session=session, username=data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate username"
        )
    if get_user_with_email(session=session, email=data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate email"
        )
    hashed_password = get_password_hash(data.password)
    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed_password
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]
):
    user = authenticate_user(session=session,
                             username=form_data.username,
                             password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRES_HOURS)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token,
            "token_type": "bearer"}


@router.get("/users/me", response_model=UserRead)
async def get_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user


@router.patch("/users/me", response_model=UserRead)
async def update_user(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    data: Annotated[UserUpdate, Body()]
):
    data: dict = data.dict(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No data provided'
        )
    else:
        new_username = data.get("username")
        if new_username:
            user_with_username = get_user_with_username(
                session=session, username=new_username
            )
            if user_with_username and (user_with_username.id != current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate username"
                )
            current_user.username = new_username
        new_email = data.get("email")
        if new_email:
            user_with_email = get_user_with_email(
                session=session, email=new_email
            )
            if user_with_email and (user_with_email.id != current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate email"
                )
            current_user.email = new_email

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user
