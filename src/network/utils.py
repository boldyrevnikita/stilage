import base64

import ezdxf
from minio import Minio

from src.network.settings import Settings


def get_dxf_doc_from_s3(key: str) -> ezdxf.document.Drawing:
    settings = Settings()
    key = f'{settings.S3_DXF_FOLDER_NAME}/{key}.dxf'

    bucket_name = settings.S3_BUCKET_NAME

    client = Minio(settings.S3_ENDPOINT,
                   access_key=settings.S3_ACCESS_KEY,
                   secret_key=settings.S3_SECRET_KEY)

    try:
        response = client.get_object(bucket_name=bucket_name, object_name=key)
        doc = ezdxf.decode_base64(base64.b64encode(response.read()))
        return doc
    except Exception as e:
        print(f"Error retrieving file from S3: {e}")
        return None
