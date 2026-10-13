from fastapi import FastAPI, Request ,HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

app.mount("/static",StaticFiles(directory="static"),name="static")
templates = Jinja2Templates(directory="templates")

posts:list[dict] = [
    {
        "id":1,
        "author":"Shreyash Dhoot",
        "title":"Stomach Ache",
        "content": "snot makes my stomach ach",
        "date_posted":"October 11,2026",
    },
    {
        "id":2,
        "author":"Sushama Dhoot",
        "title":"Foot Ache",
        "content": "Endless work makes my feet hurt",
        "date_posted":"August 11,2026",
    },
]

#HTML routes are for human viewing and are NOT needed in API documentation therefore we use include_in_schema=False
@app.get("/",include_in_schema=False)
@app.get("/post",include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts":posts ,"title":"Home"},
    )

@app.get("/post/{post_id}", include_in_schema=False)
def post_page(request: Request , post_id : int ):
    for post in posts :
        if post.get("id") == post_id:
            title = post['title'][:50]
            return templates.TemplateResponse(
                request,
                "post.html",
                {"post":post,"title": title},
                )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "Post Not found")

@app.get("/api/posts")
def get_posts():
    return posts

@app.get("/api/posts/{post_id}")
def get_post(post_id : int ):
    for post in posts :
        if post.get("id")==post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND , detail = "Post Not found")


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

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
