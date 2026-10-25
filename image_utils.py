import uuid 
from io import BytesIO
import boto3 
from starlette.concurrency import run_in_threadpool
from config import settings

from PIL import Image , ImageOps

def _get_s3_client():
    return boto3.client(
        "s3",
        region_name = settings.aws_s3_region,
        aws_access_key_id=(
            settings.aws_access_key.get_secret_value()
            if settings.aws_access_key
            else None 
        ),
        aws_secret_access_key=(
            settings.aws_access_key_secret.get_secret_value()
            if settings.aws_access_key_secret
            else None 
        ),
        endpoint_url = settings.aws_s3_endpoint_url,
    )

def process_profile_image(content:bytes)->tuple[bytes,str]:
    with Image.open(BytesIO(content)) as original : 
        img = ImageOps.exif_transpose(original)

        img = ImageOps.fit(img,(300,300), method = Image.Resampling.LANCZOS)

        if img.mode in ("RGBA" , "LA" ,"P"):
            img = img.convert("RGB")
        
        filename = f"{uuid.uuid4().hex}.jpg"
        output = BytesIO()

        img.save(output, "JPEG" , quality = 85 , optimize = True)
        output.seek(0)
    
    return output.read(),filename


def _upload_to_s3(file_bytes:bytes,key:str) -> None :
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.aws_s3_bucket_name,
        key,
        ExtraArgs={"ContentType":"image/jpeg"},
    )

def _delete_from_s3(key:str)->None :
    s3 = _get_s3_client()
    s3.delete_object(Bucket=settings.aws_s3_bucket_name,Key=key)

# since boto3 calls are blocking i.e synchronous we use run in threadpool to make it async 
async def upload_profile_image(file_bytes:bytes,filename:str)->None :
    key=f"profile_pics/{filename}" #<== shpuld match the fileformat on S3
    await run_in_threadpool(_upload_to_s3,file_bytes,key)

async def delete_profile_images(filename: str | None ) -> None :
    if filename is None :
        return 
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_delete_from_s3,key)

    