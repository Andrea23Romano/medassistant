from transformers import pipeline
import streamlit as st
import torch
from audiorecorder import audiorecorder
import numpy as np
from src.logger import get_logger

# Set up logger
logger = get_logger(name=None)

# Audio processing settings
SAMPLE_RATE = 16000


def transcribe_audio(audio_segment, pipe):
    """Transcribe audio using pipeline"""
    logger.debug("Processing audio for transcription")
    try:
        # Convert audio segment to numpy array
        audio_array = np.array(audio_segment.get_array_of_samples())

        # Create a dict with the required format for the pipeline
        audio_dict = {"array": audio_array, "sampling_rate": SAMPLE_RATE}
        result = pipe(audio_dict, batch_size=8, return_timestamps=True)
        transcription = result["chunks"][0]["text"] if result["chunks"] else ""
        logger.info("Successfully transcribed audio")
        return transcription
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
        raise


def main():
    logger.info("Starting Speech to Text application")
    st.title("Speech to Text Transcription")

    # Initialize session state
    if "transcriptions" not in st.session_state:
        st.session_state.transcriptions = []

    # Load pipeline
    @st.cache_resource
    def load_pipeline():
        logger.info("Loading Whisper pipeline")
        try:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            pipe = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-small",
                chunk_length_s=30,
                device=device,
            )
            logger.info(f"Successfully loaded pipeline on {device}")
            return pipe
        except Exception as e:
            logger.error(f"Error loading pipeline: {str(e)}", exc_info=True)
            raise

    pipe = load_pipeline()

    # Audio recorder
    audio = audiorecorder(
        "Start Recording",
        "Stop Recording",
        custom_style={"color": "black"},
        show_visualizer=True,
    )

    transcription_placeholder = st.empty()

    if len(audio) > 0:
        st.audio(audio.export().read())

        # Process and transcribe the audio
        text = transcribe_audio(audio, pipe)
        st.session_state.transcriptions.append(f"{text}")
        logger.debug(f"Added transcription: {text}")

    # Display all transcriptions
    if st.session_state.transcriptions:
        transcription_placeholder.markdown("".join(st.session_state.transcriptions))

    if st.button("Clear Transcriptions"):
        logger.info("Clearing transcription history")
        st.session_state.transcriptions = []
        transcription_placeholder.empty()


main()
