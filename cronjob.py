from src.chat_manager import SummaryManager
from src.mongo import MongoManager
from src.embedding import EmbeddingGenerator
from dotenv import load_dotenv
import streamlit as st

with st.status("Creating daily summaries...") as status:
    load_dotenv()
    mongo_manager = MongoManager()
    embedding_generator = EmbeddingGenerator()
    SummaryManager(mongo_manager, embedding_generator).create_daily_summaries()
    status.update(label="Daily summaries created successfully!", state="complete")
