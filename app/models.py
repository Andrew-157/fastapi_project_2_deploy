from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from .schemas import UserBase, RecommendationBase, FictionTypeBase, TagBase, CommentBase, ReactionBase


class User(UserBase, table=True):
    id: int | None = Field(primary_key=True, default=None)
    hashed_password: str

    recommendations: list["Recommendation"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "delete"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "delete"}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "delete"}
    )


class FictionType(FictionTypeBase, table=True):
    __tablename__ = 'fiction_type'
    id: int | None = Field(primary_key=True, default=None)

    recommendations: list["Recommendation"] = Relationship(
        back_populates="fiction_type", sa_relationship_kwargs={"cascade": "delete"}
    )


class RecommendationTagLink(SQLModel, table=True):
    __tablename__ = 'tagged_recommendations'
    recommendation_id: int | None = Field(
        default=None, foreign_key="recommendation.id", primary_key=True
    )
    tag_id: int | None = Field(
        default=None, foreign_key="tag.id", primary_key=True
    )


class Recommendation(RecommendationBase, table=True):
    id: int | None = Field(primary_key=True, default=None)
    published: datetime = Field(default=datetime.utcnow())
    updated: datetime | None = Field(default=None)
    user_id: int = Field(foreign_key="user.id")
    fiction_type_id: int = Field(
        foreign_key="fiction_type.id")

    user: User = Relationship(back_populates="recommendations")
    fiction_type: FictionType = Relationship(back_populates="recommendations")
    tags: list["Tag"] = Relationship(
        back_populates="recommendations", link_model=RecommendationTagLink
    )
    comments: list["Comment"] = Relationship(
        back_populates="recommendation", sa_relationship_kwargs={"cascade": "delete"}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="recommendation", sa_relationship_kwargs={"cascade": "delete"}
    )


class Tag(TagBase, table=True):
    id: int | None = Field(primary_key=True, default=None)

    recommendations: list["Recommendation"] = Relationship(
        back_populates="tags", link_model=RecommendationTagLink
    )


class Comment(CommentBase, table=True):
    id: int | None = Field(primary_key=True, default=None)
    published: datetime = Field(default=datetime.utcnow())
    updated: datetime | None = Field(default=None)
    user_id: int = Field(foreign_key="user.id")
    recommendation_id: int = Field(foreign_key="recommendation.id")

    user: User = Relationship(back_populates="comments")
    recommendation: Recommendation = Relationship(back_populates="comments")


class Reaction(ReactionBase, table=True):
    id: int | None = Field(primary_key=True, default=None)
    user_id: int = Field(foreign_key="user.id")
    recommendation_id: int = Field(foreign_key="recommendation.id")

    user: User = Relationship(back_populates="reactions")
    recommendation: Recommendation = Relationship(back_populates="reactions")
    __table_args__ = (UniqueConstraint('user_id', 'recommendation_id',
                                       name='user_recommendation_uc'),)
