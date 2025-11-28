import json
import re
from config.settings import settings
import boto3
import botocore
from botocore.config import Config


class ReadFSD:
    def __init__(self, doc_id):
        config = botocore.config.Config(read_timeout=900, connect_timeout=900)
        self.s3 = boto3.client("s3", region_name=settings.BUCKET_S3, config=config)
        self.doc_id = doc_id

    def get_latest_requirements_file(self):
        prefix = f"{self.doc_id}/{self.doc_id}_requirements"
        pattern = re.compile(rf"{self.doc_id}_requirements(?:(\d+))?\.md$")
        
        # s3 = boto3.client("s3")        
        paginator = self.s3.get_paginator("list_objects_v2")
        candidates = []

        for page in paginator.paginate(Bucket=settings.BUCKET_S3, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"].split("/")[-1]   # filename only, ex: 123_requirements3.md
                match = pattern.match(key)
                if match:
                    version = match.group(1)
                    version = int(version) if version else 0  # default version = 0
                    candidates.append((version, obj["Key"]))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]   # highest version file key

    def get_fsd_s3(self) -> str:

        file_key = self.get_latest_requirements_file()

        if not file_key:
            return {
                "statusCode": 404,
                "response": f"No requirements file found for {self.doc_id}"
            }

        print(f"Fetching: s3://{settings.BUCKET_S3}/{file_key}")

        response = self.s3.get_object(Bucket=settings.BUCKET_S3, Key=file_key)
        content = response["Body"].read().decode("utf-8")
        # print(content)
        
        return content