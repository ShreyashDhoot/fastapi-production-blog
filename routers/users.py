from schemas import (PostResponse , 
                    UserPublic ,
                    UserPrivate,
                    Token , 
                    UserCreate , 
                    UserUpdate,
                    PaginatedPostsResponse,
                    ChangePasswordRequest,
                    ForgotPasswordRequest,
                    ResetPasswordRequest,
                    ) 
from typing import Annotated 
from sqlalchemy import select , func
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi import (
    APIRouter ,
    HTTPException, 
    status , 
    Depends ,
    UploadFile, 
    Query,
    BackgroundTasks,
    )  
import models 
from database import get_db
from datetime import timedelta , datetime , UTC 
from fastapi.security import OAuth2PasswordRequestForm 
from auth import (
    create_access_token , 
    hash_password , 
    verify_password ,
    CurrentUser,
    generate_reset_token,
    hash_reset_token
    )
from email_utils import send_password_reset_email
from config import settings
from PIL import UnidentifiedImageError 
from starlette.concurrency import run_in_threadpool 
from image_utils import process_profile_image , delete_profile_image
from sqlalchemy import delete as sql_delete

router = APIRouter()

@router.post(
    "", #<== path in the router is relative 
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
    )

async def create_user(user:UserCreate , db: Annotated[AsyncSession,Depends(get_db)]):
    #need to check if user name already exists 
    result = await db.execute(select(models.User).where(func.lower(models.User.username == user.username)),)
    existing_user  = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "Username already exists",
        )
    
    result = await db.execute(select(models.User).where(func.lower(models.User.email == user.email)),)
    existing_user  = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "email already exists",
        )
    
    new_user = models.User(
        username = user.username,
        email = user.email.lower(),
        password_hash = hash_password(user.password),
    )

    db.add(new_user) # does not get an await adds to the sessions pending list in memory does nothing on teh i/o front
    await db.commit()
    await db.refresh(new_user)

    return new_user

@router.post("/token",response_model=Token)
async def login_for_access_token(
    form_data : Annotated[OAuth2PasswordRequestForm,Depends()],
    db :Annotated[AsyncSession,Depends(get_db)],):
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email)==form_data.username.lower())
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password , user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate":"Bearer"},
        )

    access_token_expires = timedelta(minutes = settings.access_token_expire_minutes)
    access_token = create_access_token(
        data = {"sub": str(user.id)},
        expires_delta= access_token_expires,
    )

    return Token(access_token=access_token, token_type = "bearer" )   

@router.get("/me",response_model=UserPrivate)
async def get_current_user(current_user : CurrentUser):
    return current_user

@router.post("/forgot-password",status_code = status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data : ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession,Depends(get_db)],
):
    result = await db.execute(
        select(models.User)
        .where(func.lower(models.User.email)==request_data.email.lower()),
    )

    user = result.scalars().first()

    if user: 
        await db.execute(
            sql_delete(models.PasswordResetToken)
            .where(models.PasswordResetToken.user_id==user.id,),
        )

        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes= settings.reset_token_expire_minutes
        )
        reset_token= models.PasswordResetToken(
            user_id = user.id,
            token_hash = token_hash,
            expires_at = expires_at ,
        )
        db.add(reset_token)

        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username= user.username,
            token=token,
        )

    return {
        "message" : "if an account exists with this email you will receive password reset instructions in your registered email"
    }

@router.post("/reset-password",status_code=status.HTTP_200_OK)
async def reset_password(
    request_data : ResetPasswordRequest,
    db:Annotated[AsyncSession,Depends(get_db)]):

# hash the token we have gotten from the request data from the reset passwrd schema 
    token_hash = hash_reset_token(request_data.token)

    result = await db.execute(
        select(models.PasswordResetToken)
        .where(models.PasswordResetToken.token_hash == token_hash)
    )

    reset_token = result.scalars().first()

    if not reset_token :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            details = "Invalid or expired reset token"
        )

    if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    result = await db.execute(
        select(models.User)
        .where(models.User.id==reset_token.user_id)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Invalid or expired reset token"
        )
    
    user.password_hash = hash_password(request_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken)
        .where(models.PasswordResetToken.user_id==user.id)
    )

    await db.commit()

    return{
        "message" : "Password reset is successful please reset with your new password"
    } 

@router.post("/me/password",status_code=status.HTTP_200_OK)
async def change_password(
    password_data : ChangePasswordRequest,
    current_user : CurrentUser,
    db:Annotated[AsyncSession,Depends(get_db)]):

    if not verify_password(password_data.current_password,current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            details = "Current password is incorrect",
        )

    current_user.password_hash =hash_password(password_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken)
        .where(models.PasswordResetToken.user_id == current_user.id)
    )

    await db.commit()

    return {
        "message":"Your password has been reset successfully "
        }


@router.get("/{user_id}",response_model=UserPublic)
async def get_user(user_id:int , db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),    
    )
    user = result.scalars().first()

    if user:
        return user 
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")

@router.get("/{user_id}/posts",response_model=PaginatedPostsResponse)
async def get_user_posts(
    user_id:int, 
    db:Annotated[AsyncSession , Depends(get_db)],
    skip : Annotated[int , Query(ge=0)]=0 ,
    limit : Annotated[int , Query(ge=1,le=100)] =10 ,):
    result = await db.execute(select(models.User).where(models.User.id == user_id).order_by(models.Post.date_posted.desc()))
    user = result.scalars().first()
    if not user :
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    count_results = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user.id)
        )
    total = count_results.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author)) #pydantic schema PostResponse needs post author which was earlier handles by fastap ibut now needs manual handling 
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit)
        )
    posts = result.scalars().all()

    has_more = skip + len(posts) < total 
    
    return PaginatedPostsResponse(
        posts = [PostResponse.model_calidate(post) for post in posts ],
        total = total ,
        skip =skip ,
        limit = limit ,
        has_more = has_more,
    )

@router.patch("/{user_id}",response_model=UserPrivate)
async def update_user(
    user_id : int , 
    user_data: UserUpdate ,
    current_user : CurrentUser , 
    db : Annotated[AsyncSession , Depends(get_db)]):
    if user_id != current_user.id :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail = "Not authorized to update user info")
    result = await db.execute(select(models.User).where(models.User.id==user_id))
    user = result.scalars().first()
    if not user :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = "user not found")
    if user_data.username is not None and user_data.username.lower() != user.username.lower():
        result = await db.execute(select(models.User).where(func.lower(models.User.username)==user_data.username.lower()))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    if user_data.email is not None and user_data.email.lower() != user.email.lower():
        result = await db.execute(
            select(models.User)
            .where(func.lower(models.User.email) == user_data.email.lower()),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )    
    
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user,field,value.lower())

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user :CurrentUser, 
    db: Annotated[AsyncSession, Depends(get_db)]):
    if user.user_id != current_user.id :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail = "Not authorized to delete user")
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_filename = user.image_file
    await db.delete(user)
    await db.commit()

    if old_filename:
        delete_profile_image(old_filename)

@router.patch("/{user_id}/picture",response_model=UserPrivate)
async def upload_profile_picture(
    user_id :int ,
    file :UploadFile,
    current_user : CurrentUser,
    db : Annotated[AsyncSession, Depends(get_db)],
    ):
    if current_user.id != user_id :
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not authorized to update this users picture",
        )
    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Image size too big upload image smaller that 5 mb",
        )

    try : 
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err :
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid Image file type only .jpg or .jpeg allowed",
        )
    
    old_filename = current_user.image_file 

    current_user.image_file = new_filename 
    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)
    
    return current_user

@router.delete("/{user_id}/picture",response_model=UserPrivate)
async def delete_user_picture(
    user_id :int ,
    current_user : CurrentUser,
    db : Annotated[AsyncSession, Depends(get_db)],
    ):
    if current_user.id != user_id :
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not authorized to delete this users picture",
        )
    
    old_filename = current_user.image_file

    if old_filename is None :
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "No profile picture to delete ",
        ) 

    current_user.image_file = None  
    await db.commit()
    await db.refresh(current_user)

    delete_profile_image(old_filename)
    
    return current_user



