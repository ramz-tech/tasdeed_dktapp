import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Dict, List
from config.config import AppConfig


class MongoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            config = AppConfig()
            try:
                client = MongoClient(config.MONGODB_URI)
                cls._instance = super(MongoDBClient, cls).__new__(cls)
                cls._instance.client = client
                cls._instance.db = client['bills']
                cls._instance.collection = cls._instance.db["extracted_text"]
            except PyMongoError as e:
                logger.critical(f"Failed to connect to MongoDB: {e}")
                raise
        return cls._instance

    def insert_data(self, data: Dict, task_id: str) -> None:
        """Insert data into MongoDB with associated task_id."""
        if not isinstance(data, dict):
            logger.error("Data must be a dictionary for MongoDB insertion.")
            return
        # Convert keys to strings if they aren't already
        data = {str(k): v for k, v in data.items()}
        for record in data.values():
            if isinstance(record, dict):
                record['task_id'] = task_id
                self.collection.insert_one(record)
            else:
                logger.error("Invalid record format when saving to MongoDB.")

    def get_docs_by_task(self, task_id: str) -> List[Dict]:
        return list(self.collection.find({'task_id': task_id}, {'_id': 0, 'task_id': 0}))

    def count_docs_by_task(self, task_id: str) -> int:
        return self.collection.count_documents({'task_id': task_id})
