from io import BytesIO
from botocore.exceptions import BotoCoreError , ClientError
from config import settings
from image_utils import _get_s3_client

def check_s3_connection():
    s3 = _get_s3_client()

    print(f"Bucket: {settings.aws_s3_bucket_name}")
    print(f"Region: {settings.aws_s3_region}")
    print()

    test_key = "profile_pics/test.txt"

    try:
        s3.upload_fileobj(
            BytesIO(b"test"),
            settings.aws_s3_bucket_name,
            test_key,
            ExtraArgs={"ContentType":"text/plain"},
        )
        print("Upload: SUCCESSFUL ")

    except (BotoCoreError,ClientError) as e:
        print(f"Upload:FAILED - {e}")
        return 

    try:
        s3.delete_object(Bucket=settings.aws_s3_bucket_name,Key=test_key)
        print("Delete : SUCCESS")
    except (BotoCoreError , ClientError) as e:
        print(f"Delete : Failed - {e}")

    print()
    print("All tests passed ! your S3 config is working")

if __name__ =="__main__":
    check_s3_connection()