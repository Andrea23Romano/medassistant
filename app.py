import streamlit as st
from src.mongo import MongoManager
from src.models import User, Message, ConversationEntry
from datetime import datetime
import uuid
from src.logger import get_logger
from dotenv import load_dotenv
from src.utils import hash_password
from src.openai import DailyAgent
from src.embedding import EmbeddingGenerator
from src.CONSTANTS import DEFAULT_SYSTEM_PROMPT, N_PREVIOUS_DAYS
from datetime import date, timedelta

# Load environment variables from a .env file
load_dotenv()
# Initialize MongoManager and logger
mongo_manager = MongoManager()
logger = get_logger(__name__)
embedder = EmbeddingGenerator()


def main():
    st.title("Meddy")

    # Initialize session state
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.authenticated:
        # Create tabs for login and signup
        tab1, tab2 = st.tabs(["Accedi", "Registrati"])

        with tab1:
            st.subheader("Accedi")
            login_user_id = st.text_input("ID Utente", key="login_user_id")
            login_password = st.text_input(
                "Password", type="password", key="login_password"
            )

            if st.button("Accedi"):
                try:
                    # Hash the login password before checking
                    hashed_password = hash_password(login_password)
                    if mongo_manager.check_user(login_user_id, hashed_password):
                        st.session_state.authenticated = True
                        st.session_state.user_id = login_user_id
                        st.success("Accesso effettuato con successo!")
                        st.rerun()
                    else:
                        st.error("Credenziali non valide")
                except Exception as e:
                    logger.error(f"Login error: {str(e)}")
                    st.error("Si è verificato un errore durante l'accesso")

        with tab2:
            st.subheader("Registrati")
            new_user_id = st.text_input("ID Utente", key="new_user_id")
            full_name = st.text_input("Nome Completo", key="full_name")
            email = st.text_input("Email", key="email")
            new_password = st.text_input(
                "Password", type="password", key="new_password"
            )
            confirm_password = st.text_input(
                "Conferma Password", type="password", key="confirm_password"
            )

            if st.button("Registrati"):
                if new_password != confirm_password:
                    st.error("Le password non coincidono!")
                elif not full_name or not email:
                    st.error("Per favore compila tutti i campi!")
                else:
                    try:
                        users = mongo_manager.get_users()
                        if any(user["user_id"] == new_user_id for user in users):
                            st.error("ID Utente già esistente!")
                        else:
                            # Hash the password before storing
                            hashed_password = hash_password(new_password)
                            new_user = User(
                                user_id=new_user_id,
                                password=hashed_password,  # Store hashed password
                                name=full_name,
                                email=email,
                                created_at=datetime.now(),
                            )
                            mongo_manager.create_user(new_user)
                            st.success(
                                "Account creato con successo! Effettua il login."
                            )
                    except Exception as e:
                        logger.error(f"Signup error: {str(e)}")
                        st.error("Si è verificato un errore durante la registrazione")

    else:
        st.write(f"Benvenuto, {st.session_state.user_id}!")
        # Initialize chat interface
        if "messages" not in st.session_state:
            # Get previous interactions for this user
            previous_interactions = ""  # You'll need to implement this
            # Get previous N days of summaries
            end_date = date.today()
            start_date = end_date - timedelta(days=N_PREVIOUS_DAYS)
            summaries = mongo_manager.get_summaries_by_date_range(start_date, end_date)

            # Build text block from summaries
            previous_interactions = "\n".join(
                [
                    f"Day {s['day'].strftime('%Y-%m-%d')}:\n{s['summary']}"
                    for s in summaries
                ]
            )

            n_days = len(summaries)
            n_days = 0  # You'll need to implement this

            # Format the system prompt
            formatted_prompt = DEFAULT_SYSTEM_PROMPT.format(
                patient=st.session_state.user_id,
                n=n_days,
                previous_interactions_block=previous_interactions,
            )

            st.session_state.messages = [
                Message(role="system", content=formatted_prompt)
            ]

        # Display chat messages
        for message in st.session_state.messages:
            if message.role != "system":
                with st.chat_message(message.role):
                    st.markdown(message.content)

        # Handle user input
        if prompt := st.chat_input("Come posso aiutarti?"):
            # Add user message
            user_message = Message(
                role="user", content=prompt, timestamp=datetime.now()
            )
            st.session_state.messages.append(user_message)
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get AI response
            agent = DailyAgent()
            try:
                chat_history = agent.create(chat_history=st.session_state.messages)
                assistant_message = chat_history[-1]
                st.session_state.messages.append(assistant_message)
                with st.chat_message("assistant"):
                    st.markdown(assistant_message.content)

                # Store conversation in MongoDB
                conversation = ConversationEntry(
                    session_id=st.session_state.session_id,
                    user_id=st.session_state.user_id,
                    messages=st.session_state.messages,
                    text_content=" ".join(
                        [msg.content for msg in st.session_state.messages]
                    ),
                    text_embedding=embedder.generate_embedding(
                        " ".join([msg.content for msg in st.session_state.messages])
                    ),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )

                # Check if conversation exists
                existing_conversation = mongo_manager.get_conversation_by_session_id(
                    st.session_state.session_id
                )
                if existing_conversation:
                    # Update existing conversation
                    conversation.created_at = (
                        existing_conversation.created_at
                    )  # Preserve original creation date
                    mongo_manager.update_conversation(
                        st.session_state.session_id, conversation
                    )
                else:
                    # Create new conversation
                    mongo_manager.create_conversation(conversation)
            except Exception as e:
                logger.error(f"Chat error: {str(e)}")
                st.error(
                    "Si è verificato un errore durante la generazione della risposta"
                )
        if st.sidebar.button("Disconnetti"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.rerun()


if __name__ == "__main__":
    main()
