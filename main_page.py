import streamlit as st
from src.mongo import MongoManager
from src.models import User
from datetime import datetime
import uuid
from src.logger import get_logger
from dotenv import load_dotenv
from src.utils import hash_password
from src.embedding import EmbeddingGenerator
from src.chat_manager import ChatManager

logger = get_logger(name=None, log_level="INFO")

DEBUG = False  # Set this to True to enable debug mode
TEST_USER = "TestUser"


class SessionManager:
    @staticmethod
    def initialize_session():
        if DEBUG:
            st.session_state.authenticated = True
            st.session_state.user_id = TEST_USER
            st.session_state.name = "Test User"
            st.success("DEBUG mode: Logged in as TEST_USER")

        if "session_id" not in st.session_state:
            st.session_state.timestamp = datetime.now()
            st.session_state.session_id = str(uuid.uuid4())
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "user_id" not in st.session_state:
            st.session_state.user_id = None


class Authentication:
    def __init__(self, mongo_manager):
        self.mongo_manager = mongo_manager

    def login(self, user_id, password):
        try:
            hashed_password = hash_password(password)
            if name := self.mongo_manager.check_user(user_id, hashed_password):
                st.session_state.authenticated = True
                st.session_state.user_id = user_id
                st.session_state.name = name
                st.success("Accesso effettuato con successo!")
                st.rerun()
            else:
                st.error("Credenziali non valide")
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            st.error("Si è verificato un errore durante l'accesso")

    def register(self, user_id, full_name, email, password, confirm_password):
        if password != confirm_password:
            st.error("Le password non coincidono!")
            return
        if not full_name or not email:
            st.error("Per favore compila tutti i campi!")
            return

        try:
            users = self.mongo_manager.get_users()
            if any(user["user_id"] == user_id for user in users):
                st.error("ID Utente già esistente!")
                return

            hashed_password = hash_password(password)
            new_user = User(
                user_id=user_id,
                password=hashed_password,
                name=full_name,
                email=email,
                created_at=datetime.now(),
            )
            self.mongo_manager.create_user(new_user)
            st.success("Account creato con successo! Effettua il login.")
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            st.error("Si è verificato un errore durante la registrazione")


def main():
    load_dotenv()
    mongo_manager = MongoManager()
    embedder = EmbeddingGenerator()

    st.title("Meddy")
    if st.button("Disconnetti"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.experimental_rerun()
    SessionManager.initialize_session()

    if not st.session_state.authenticated:
        auth = Authentication(mongo_manager)
        show_auth_interface(auth)
    else:
        chat_manager = ChatManager(
            mongo_manager,
            embedder,
            st.session_state.name,
            st.session_state.session_id,
            st.session_state.user_id,
        )
        show_chat_interface(chat_manager)


def show_auth_interface(auth):
    tab1, tab2 = st.tabs(["Accedi", "Registrati"])

    with tab1:
        st.subheader("Accedi")
        login_user_id = st.text_input("ID Utente", key="login_user_id")
        login_password = st.text_input(
            "Password", type="password", key="login_password"
        )
        if st.button("Accedi"):
            auth.login(login_user_id, login_password)

    with tab2:
        st.subheader("Registrati")
        new_user_id = st.text_input("ID Utente", key="new_user_id")
        full_name = st.text_input("Nome Completo", key="full_name")
        email = st.text_input("Email", key="email")
        new_password = st.text_input("Password", type="password", key="new_password")
        confirm_password = st.text_input(
            "Conferma Password", type="password", key="confirm_password"
        )
        if st.button("Registrati"):
            auth.register(new_user_id, full_name, email, new_password, confirm_password)


def show_chat_interface(chat_manager):
    st.write(f"Benvenuto, {st.session_state.user_id}!")
    chat_manager.initialize_chat()

    session_start = st.session_state.timestamp
    separator_shown = False

    for message in chat_manager.messages:
        if (
            not separator_shown
            and message.timestamp > session_start
            and message.role != "system"
        ):
            with st.chat_message("system"):
                st.markdown("---")  # Horizontal line
                st.markdown(
                    f"<div style='text-align: center; color: gray; font-size: 0.8em; margin: -15px 0;'>{session_start.strftime('%H:%M')} - Nuova sessione</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")  # Horizontal line

        if message.role != "system":
            with st.chat_message(message.role):
                st.markdown(message.content)
                st.markdown(
                    f"<span style='color: gray; font-size: 0.8em;'>{message.timestamp.strftime('%H:%M')}</span>",
                    unsafe_allow_html=True,
                )

    if prompt := st.chat_input("Come posso aiutarti?"):
        with st.chat_message("user"):
            st.markdown(prompt)
            st.markdown(
                f"<span style='color: gray; font-size: 0.8em;'>{message.timestamp.strftime('%H:%M')}</span>",
                unsafe_allow_html=True,
            )

        if assistant_message := chat_manager.handle_chat_input(prompt):
            with st.chat_message("assistant"):
                st.markdown(assistant_message.content)
                st.markdown(
                    f"<span style='color: gray; font-size: 0.8em;'>{message.timestamp.strftime('%H:%M')}</span>",
                    unsafe_allow_html=True,
                )


main()
