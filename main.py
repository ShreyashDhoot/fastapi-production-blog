from fastapi import FastAPI, Request ,HTTPException, status , Depends 
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from schemas import (PostCreate,
                    PostResponse , 
                    UserResponse , 
                    UserCreate , 
                    PostUpdate ,
                    UserUpdate) 
from typing import Annotated 
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

import models 
from database import Base , engine , get_db

#lifespan function startup and shutdown 
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs at startup until yeild 
    async with engine.begin() as conn :
        await conn.run_sync(Base.metadata.create_all)
    yield 
    # runs at shutdown 
    await engine.dispose()

app = FastAPI(lifespan = lifespan)

app.mount("/static",StaticFiles(directory="static"),name="static")
app.mount("/media",StaticFiles(directory="media"),name="media")
templates = Jinja2Templates(directory="templates")

#HTML routes are for human viewing and are NOT needed in API documentation therefore we use include_in_schema=False
@app.get("/",include_in_schema=False,name="home")
@app.get("/post",include_in_schema=False,name="posts")
async def home(request: Request , db : Annotated[AsyncSession ,Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts":posts ,"title":"Home"},
    )

@app.get("/post/{post_id}", include_in_schema=False)
async def post_page(request: Request , post_id : int ,db : Annotated[AsyncSession, Depends(get_db)]):
    results = await db.execute(
        select(models.post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id))
    post = results.scalar().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post":post,"title": title},
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "Post Not found")

@app.get("/users/{user_id}/posts",include_in_schema=False,name="user_posts")
async def user_posts_page(
    request : Request, 
    user_id : int,
    db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id))

    user = result.scalars().first()
    if not user :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,details="User not found")
    
    results = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id==user_id)
        )
    posts = results.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts":posts,"user":user,"title":f"{user.username}'s Posts"
        },
    )

#================================================================================
#                                 API Routes 
#================================================================================

@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    )

async def create_user(user:UserCreate , db: Annotated[AsyncSession,Depends(get_db)]):
    #need to check if user name already exists 
    result = await db.execute(select(models.User).where(models.User.username == user.username),)
    existing_user  = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "Username already exists",
        )
    
    result = await db.execute(select(models.User).where(models.User.email == user.email),)
    existing_user  = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "email already exists",
        )
    
    new_user = models.User(
        username = user.username,
        email = user.email,
    )

    db.add(new_user) # does not get an await adds to the sessions pending list in memory does nothing on teh i/o front
    await db.commit()
    await db.refresh(new_user)

    return new_user 
    
@app.get("/api/users/{user_id}",response_model=UserResponse)
async def get_user(user_id:int , db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),    
    )
    user = result.scalars().first()

    if user:
        return user 
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")

@app.get("api/users/{user_id}/posts",response_model=list[PostResponse])
async def get_user_posts(user_id:int, db:Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author)) #pydantic schema PostResponse needs post author which was earlier handles by fastap ibut now needs manual handling 
        .where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

@app.patch("/api/users/{user_id}",response_model=UserResponse)
async def update_user(user_id : int , user_data: UserUpdate , db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id==user_id))
    user = result.scalars().first()
    if not user :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = "user not found")
    if user_data.username is not None and user_data.username != user.username:
        result = await db.execute(select(models.User).where(models.User.username==user_data.username))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    if user_data.email is not None and user_data.email != user.email:
        result = await db.execute(
            select(models.User)
            .where(models.User.email == user_data.email),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )    
    
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user,field,value)

    await db.commit()
    await db.refresh(user)
    return user

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()

@app.get("/api/posts", response_model =list[PostResponse]) #<-- validates that each post follows our post response schemas 
async def get_posts( db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = results.scalar().all()
    return posts

@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code = status.HTTP_201_CREATED,
    )

async def create_post(post:PostCreate, db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(
        select(models.User)
        .where(models.User.id==post.user_id))
    user = results.scalar()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            details="User not found"
        )

    new_post = models.Post(
        title = post.title,
        content= post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post ,attribute_names=['author'])
    return new_post 


@app.get("/api/posts/{post_id}" , response_model = PostResponse)
async def get_post(post_id : int , db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = results.scalars().first()
    if post :
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "Post Not found")

@app.put("/api/posts/{post_id}",response_model=PostResponse)
async def update_post_full(post_id : int , post_data: PostCreate , db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,details = "post not found")
    if post_data.user_id != post.user_id:
        results = await db.execute(select(models.User).where(models.User.id==post.user_id))
        user = results.scalar()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                details="User not found"
            )
    post.title = post_data.title 
    post.content = post_data.content 
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names = ["author"])
    return post

@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def partial_update(post_id : int , post_data : PostUpdate , db : Annotated[AsyncSession, Depends(get_db)]):
    #checking if the post user wants to update exists 
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,details = "post not found")
    
    update_data = post_data.model_dump(exclude_unset=True) #<== only changes what is comming in 
    for field , value in update_data.items():
        setattr(post,field,value)

    await db.commit()
    await db.refresh(post ,attribute_names=['author'])
    return post

@app.delete("/api/posts/{post_id}",response_model=None)
async def delete_post(post_id : int , db : Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,details = "post not found")
    
    await db.delete(post)
    await db.commit()
    return "post is deleted"


#===============================================================
# Exception handlers 
#================================================================
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request , exception)
    
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request , exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
