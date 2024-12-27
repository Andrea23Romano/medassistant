import streamlit as st
from src.logger import get_logger

logger = get_logger(name=None, log_level="INFO")

pages = {
    "Meddy": [
        st.Page("main_page.py", title="Meddy"),
    ],
    "Dev": [
        st.Page("cronjob.py", title="Summary Cron Job"),
        st.Page("debug_mode_page.py", title="Debug Mode"),
    ],
}

pg = st.navigation(pages, position="hidden")
pg.run()
