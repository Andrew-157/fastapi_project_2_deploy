import re
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import validator

# User schemas


class UserBase(SQLModel):
    username: str = Field(max_length=255, min_length=5,
                          unique=True, index=True)

    email: str = Field(max_length=255, unique=True,
                       index=True)

    @validator("email")
    def email_valid(cls, value):
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, value):
            raise ValueError("Not valid email address")
        return value


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int


class UserUpdate(SQLModel):
    username: str = Field(max_length=255, min_length=5,
                          default=None)
    email: str = Field(max_length=255, default=None)

    @validator("email")
    def email_valid(cls, value):
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, value):
            raise ValueError("Not valid email address")
        return value


# FictionType schemas
class FictionTypeBase(SQLModel):
    name: str = Field(min_length=4,
                      max_length=255,
                      unique=True)
    slug: str = Field(min_length=4, max_length=300,
                      unique=True)


class FictionTypeRead(FictionTypeBase):
    id: int


# Tag schemas
class TagBase(SQLModel):
    name: str = Field(unique=True, max_length=255,
                      min_length=4)


class TagRead(TagBase):
    id: int


# Recommendation schemas
class RecommendationBase(SQLModel):
    title: str = Field(max_length=255)
    short_description: str
    opinion: str


class RecommendationCreate(RecommendationBase):
    fiction_type: str = Field(min_length=4,
                              max_length=255,
                              unique=True)
    tags: list[str] = Field(min_items=1)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Whiplash",
                    "short_description": "Music drama about young musician pursuing his dream",
                    "opinion": "Amazing piece of art, I recommend watching it to everyone",
                    "fiction_type": "movie",
                    "tags": ["music", "drama", "jazz",]
                }
            ]
        }
    }


class RecommendationRead(RecommendationBase):
    id: int
    user_id: int
    published: datetime
    updated: datetime | None
    fiction_type: FictionTypeRead
    tags: list[TagRead]


class RecommendationUpdate(SQLModel):
    title: str | None = Field(max_length=255, default=None)
    short_description: str | None = Field(default=None)
    opinion: str | None = Field(default=None)
    fiction_type: str | None = Field(min_length=4,
                                     max_length=255,
                                     default=None)
    tags: list[str] | None = Field(min_items=1,
                                   default=None)


# Comment schemas
class CommentBase(SQLModel):
    content: str


class CommentRead(CommentBase):
    id: int
    user_id: int
    recommendation_id: int
    published: datetime
    updated: datetime | None


class CommentCreate(CommentBase):
    pass

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Thank you for recommendation, amazing movie"
                }
            ]
        }
    }


class CommentUpdate(SQLModel):
    content: str


# Reaction Schemas
class ReactionBase(SQLModel):
    is_positive: bool


class ReactionCreate(ReactionBase):
    pass


class ReactionRead(ReactionBase):
    id: int
    user_id: int
    recommendation_id: int


class ReactionUpdate(SQLModel):
    is_positive: bool
