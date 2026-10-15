from fastapi import APIRouter,HTTPException, status , Depends 
from schemas import (PostCreate,
                    PostResponse , 
                    PostUpdate ) 
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
from database import  get_db

router = APIRouter()


@router.get("", response_model =list[PostResponse]) #<-- validates that each post follows our post response schemas 
async def get_posts( db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = results.scalar().all()
    return posts

@router.post(
    "",
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


@router.get("/{post_id}" , response_model = PostResponse)
async def get_post(post_id : int , db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = results.scalars().first()
    if post :
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "Post Not found")

@router.put("/{post_id}",response_model=PostResponse)
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

@router.patch("/{post_id}", response_model=PostResponse)
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

@router.delete("/{post_id}",response_model=None)
async def delete_post(post_id : int , db : Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,details = "post not found")
    
    await db.delete(post)
    await db.commit()
    return "post is deleted"