import os
from dotenv import load_dotenv

class AppConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            load_dotenv()
            instance = super(AppConfig, cls).__new__(cls)
            instance.MONGODB_URI = os.environ.get('MONGODB_URI')
            instance.SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')
            if not instance.MONGODB_URI:
                raise ValueError("MONGODB_URI environment variable must be set.")
            instance.OUTPUT_DIRECTORY = 'bills'
            os.makedirs(instance.OUTPUT_DIRECTORY, exist_ok=True)
            cls._instance = instance
        return cls._instance