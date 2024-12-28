from typing import List, Optional
import os
from pymongo import MongoClient
import logging
from src.models import ConversationEntry, SummaryEntry, DocumentEntry, User
from datetime import date, datetime


class MongoManager:
    """Manager for MongoDB operations with hybrid search capabilities"""

    def __init__(self, db_name: str = "medassistant"):
        self.logger = logging.getLogger()
        try:
            self.client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
            self.db = self.client[db_name]
            self.conversations = self.db.conversations
            self.summaries = self.db.summaries
            self.documents = self.db.documents
            self.users = self.db.users
            self.logger.info(f"Successfully connected to MongoDB database: {db_name}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def create_conversation(self, conversation: ConversationEntry) -> str:
        try:
            result = self.conversations.insert_one(conversation.dict())
            self.logger.info(f"Created new conversation with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {str(e)}")
            raise

    def create_summary(self, summary: SummaryEntry) -> str:
        try:
            result = self.summaries.insert_one(summary.dict())
            self.logger.info(f"Created new summary with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to create summary: {str(e)}")
            raise

    def create_document(self, document: DocumentEntry) -> str:
        try:
            result = self.documents.insert_one(document.dict())
            self.logger.info(f"Created new document with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to create document: {str(e)}")
            raise

    def create_user(self, user: User) -> str:
        try:
            result = self.users.insert_one(user.dict())
            self.logger.info(f"Created new user with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to create user: {str(e)}")
            raise

    def update_conversation(self, session_id: str, updates: dict):
        try:
            self.conversations.update_one({"session_id": session_id}, {"$set": updates})
            self.logger.info(f"Updated conversation: {session_id}")
        except Exception as e:
            self.logger.error(f"Failed to update conversation {session_id}: {str(e)}")
            raise

    def update_summary(self, summary_id: str, updates: dict):
        try:
            self.summaries.update_one({"summary_id": summary_id}, {"$set": updates})
            self.logger.info(f"Updated summary: {summary_id}")
        except Exception as e:
            self.logger.error(f"Failed to update summary {summary_id}: {str(e)}")
            raise

    def update_document(self, document_id: str, updates: dict):
        try:
            self.documents.update_one({"document_id": document_id}, {"$set": updates})
            self.logger.info(f"Updated document: {document_id}")
        except Exception as e:
            self.logger.error(f"Failed to update document {document_id}: {str(e)}")
            raise

    def update_user(self, user_id: str, updates: dict):
        try:
            self.users.update_one({"user_id": user_id}, {"$set": updates})
            self.logger.info(f"Updated user: {user_id}")
        except Exception as e:
            self.logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise

    def hybrid_search(
        self,
        collection_name: str,
        text_query: str = None,
        embedding_query: List[float] = None,
        filters: dict = None,
        limit: int = 10,
    ) -> List[dict]:
        """
        Perform hybrid search using text and vector similarity
        """
        try:
            collection = getattr(self, collection_name)
            pipeline = []

            # Apply filters if provided
            if filters:
                pipeline.append({"$match": filters})

            # Text search
            if text_query:
                pipeline.append(
                    {
                        "$match": {
                            "$or": [
                                {"keywords": {"$in": text_query.split()}},
                                {
                                    "text_content": {
                                        "$regex": text_query,
                                        "$options": "i",
                                    }
                                },
                            ]
                        }
                    }
                )

            # Vector similarity search
            if embedding_query:
                pipeline.extend(
                    [
                        {
                            "$set": {
                                "similarity": {
                                    "$reduce": {
                                        "input": {
                                            "$range": [0, {"$size": "$embedding"}]
                                        },
                                        "initialValue": 0,
                                        "in": {
                                            "$add": [
                                                "$$value",
                                                {
                                                    "$multiply": [
                                                        {
                                                            "$arrayElemAt": [
                                                                "$embedding",
                                                                "$$this",
                                                            ]
                                                        },
                                                        {
                                                            "$arrayElemAt": [
                                                                embedding_query,
                                                                "$$this",
                                                            ]
                                                        },
                                                    ]
                                                },
                                            ]
                                        },
                                    }
                                }
                            }
                        },
                        {"$sort": {"similarity": -1}},
                    ]
                )

            pipeline.append({"$limit": limit})

            results = list(collection.aggregate(pipeline))
            self.logger.info(
                f"Hybrid search completed in {collection_name}, found {len(results)} results"
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to perform hybrid search: {str(e)}")
            raise

    def get_users(self) -> List[dict]:
        try:
            results = list(self.users.find())
            self.logger.info(f"Retrieved {len(results)} users")
            return results
        except Exception as e:
            self.logger.error(f"Failed to get users: {str(e)}")
            raise

    def check_user(self, user_id: str, password: str) -> bool:
        try:
            result = self.users.find_one({"user_id": user_id, "password": password})
            if result:
                self.logger.info(f"User {user_id} authenticated")
                return result["name"]
            else:
                self.logger.warning(f"Invalid credentials for user {user_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to authenticate user {user_id}: {str(e)}")
            raise

    def get_conversations_by_user(self, user_id: str) -> List[dict]:
        try:
            results = list(self.conversations.find({"user_id": user_id}))
            self.logger.info(
                f"Retrieved {len(results)} conversations for user: {user_id}"
            )
            return results
        except Exception as e:
            self.logger.error(
                f"Failed to get conversations for user {user_id}: {str(e)}"
            )
            raise

    def get_conversation_by_session_id(self, session_id: str) -> Optional[dict]:
        try:
            result = self.conversations.find_one({"session_id": session_id})
            if result:
                self.logger.info(f"Retrieved conversation: {session_id}")
                return result
            else:
                self.logger.warning(f"Conversation not found: {session_id}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get conversation {session_id}: {str(e)}")
            raise

    def get_conversations_by_date_range(
        self, user_id: str, start_date: date, end_date: date
    ) -> List[dict]:
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            results = list(
                self.conversations.find(
                    {
                        "user_id": user_id,
                        "created_at": {"$gte": start_datetime, "$lte": end_datetime},
                    }
                )
            )
            self.logger.info(
                f"Retrieved {len(results)} conversations for user {user_id} between {start_datetime} and {end_datetime}"
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to get conversations for date range: {str(e)}")
            raise

    def get_summaries_by_date_range(
        self, user_id: str, start_date: date, end_date: date
    ) -> List[dict]:
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            results = list(
                self.summaries.find(
                    {
                        "user_id": user_id,
                        "day": {"$gte": start_datetime, "$lte": end_datetime},
                    }
                )
            )
            self.logger.info(
                f"Retrieved {len(results)} summaries for user {user_id} between {start_datetime} and {end_datetime}"
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to get summaries for date range: {str(e)}")
            raise

    def get_last_summaries_by_user(self, user_id: str, last_n: int = 5) -> List[dict]:
        try:
            results = list(
                self.summaries.find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(last_n)
            )
            self.logger.info(
                f"Retrieved last {len(results)} summaries for user {user_id}"
            )
            return results
        except Exception as e:
            self.logger.error(
                f"Failed to get last summaries for user {user_id}: {str(e)}"
            )
            raise

    def get_document_by_id(self, user_id: str, document_id: str) -> Optional[dict]:
        try:
            result = self.documents.find_one(
                {"user_id": user_id, "document_id": document_id}
            )
            self.logger.info(f"Retrieved document {document_id} for user {user_id}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to get document {document_id}: {str(e)}")
            raise
