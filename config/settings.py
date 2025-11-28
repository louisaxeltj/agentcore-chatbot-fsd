import os
from dotenv import load_dotenv


load_dotenv()

class BaseSettings:
    APP_NAME = "Agent Core FSD Chatbot"
    ENV = os.environ.get("ENV", "development") 
    VERBOSE = bool(os.getenv("VERBOSE", True))
    VERSION_STR = os.getenv("VERSION_STR", "")
    REGION_S3 = os.getenv("REGION_S3", "")
    BUCKET_S3 = os.getenv("BUCKET_S3", "")
    MODEL_ID = os.getenv("MODEL_ID", "")
    REGION_BEDROCK = os.getenv("REGION_BEDROCK", "")

class DevelopmentSettings(BaseSettings):
    DEBUG = True
    VERSION_STR = BaseSettings.VERSION_STR + "/dev"


class ProductionSettings(BaseSettings):
    DEBUG = False
    VERSION_STR = BaseSettings.VERSION_STR + "/prod"


def get_settings():
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()


settings  = get_settings()