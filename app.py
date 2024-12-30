import streamlit as st
from src.logger import get_logger
from dotenv import load_dotenv
from datetime import datetime
import uuid


class SessionManager:
    @staticmethod
    def initialize_session(DEBUG=False, TEST_USER="TestUser"):
        if DEBUG:
            st.session_state.authenticated = True
            st.session_state.user_id = TEST_USER
            st.session_state.name = "Test User"
            st.session_state.log_level = "DEBUG"
            st.success("DEBUG mode: Logged in as TEST_USER")

        if "log_level" not in st.session_state:
            st.session_state.log_level = "INFO"
        if "session_id" not in st.session_state:
            st.session_state.timestamp = datetime.now()
            st.session_state.session_id = str(uuid.uuid4())
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "user_id" not in st.session_state:
            st.session_state.user_id = None


load_dotenv()
SessionManager.initialize_session()
logger = get_logger(
    name=None,
    log_level=st.session_state.log_level,
    session_id=st.session_state.session_id,
)
logger.info("Session {} initialized".format(st.session_state.session_id))

pages = {
    "Meddy": [
        st.Page("main_page.py", title="Meddy"),
    ],
    "Dev": [
        st.Page("cronjob.py", title="Summary Cron Job"),
        st.Page("debug_mode_page.py", title="Debug Mode"),
        st.Page("logger_page.py", title="Logger"),
        st.Page("stt_page.py", title="Speech to Text"),
    ],
}

pg = st.navigation(pages, position="hidden")
pg.run()
