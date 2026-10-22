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
from auth import CurrentUser

router = APIRouter()


@router.get("", response_model =list[PostResponse]) #<-- validates that each post follows our post response schemas 
async def get_posts( db: Annotated[AsyncSession,Depends(get_db)]):
    results = await db.execute(select(models.Post).options(selectinload(models.Post.author)).order_by(models.Post.date_posted.desc()))
    posts = results.scalars().all()
    return posts

@router.post(
    "",
    response_model=PostResponse,
    status_code = status.HTTP_201_CREATED,
    )

async def create_post(post:PostCreate,current_user:CurrentUser ,db: Annotated[AsyncSession,Depends(get_db)]):

    new_post = models.Post(
        title = post.title,
        content= post.content,
        user_id=current_user.id,
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
async def update_post_full(post_id : int , post_data: PostCreate ,current_user:CurrentUser ,db : Annotated[AsyncSession , Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = "post not found")
    
    if post.user_id != current_user.id :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail = "Not authorized to update post")
    
    post.title = post_data.title 
    post.content = post_data.content 

    await db.commit()
    await db.refresh(post, attribute_names = ["author"])
    return post

@router.patch("/{post_id}", response_model=PostResponse)
async def partial_update(post_id : int , post_data : PostUpdate ,current_user : CurrentUser ,db : Annotated[AsyncSession, Depends(get_db)]):
    #checking if the post user wants to update exists 
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = "post not found")
    
    if post.user_id != current_user.id :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail = "Not authorized to update post")

    update_data = post_data.model_dump(exclude_unset=True) #<== only changes what is comming in 
    for field , value in update_data.items():
        setattr(post,field,value)

    await db.commit()
    await db.refresh(post ,attribute_names=['author'])
    return post

@router.delete("/{post_id}",response_model=None)
async def delete_post(post_id : int , current_user : CurrentUser ,db : Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id==post_id))
    post = result.scalars().first()
    if not post :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = "post not found")

    if post.user_id != current_user.id :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail = "Not authorized to delete this post")

    await db.delete(post)
    await db.commit()
    return HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail = "post has been deleted")