from pydantic import BaseModel ,ConfigDict , Field , EmailStr
from datetime import datetime


class UserBase(BaseModel):
    username : str = Field(min_length=1,max_length=50)
    email: EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config=ConfigDict(from_attributes=True)

    id: int
    image_file:str | None 
    image_path :str 

# uses these typehints to enforce data safety at runtime 
class PostBase(BaseModel):
    #shared between creating and returning post 
    title : str = Field(min_length=1,max_length=100)
    content : str = Field(min_length=1)

class PostCreate(PostBase):
    user_id :int #Temperory 


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True) #<== gives ability to read data from objects with attributes not just dictionaries 

    id: int 
    user_id : int 
    date_posted : datetime
    author : UserResponse

