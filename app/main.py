from fastapi import FastAPI

from .routers import users, recommendations, comments, reactions

app = FastAPI()


app.include_router(users.router)
app.include_router(recommendations.router)
app.include_router(comments.router)
app.include_router(reactions.router)


@app.get("/")
async def root():
    return {"is_root": True}
