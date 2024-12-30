from transformers import pipeline
import sounddevice as sd
import numpy as np
import streamlit as st
import time
import torch
from scipy.signal import butter, filtfilt
from src.logger import get_logger

# Set up logger
logger = get_logger(name=None)

# Audio processing settings
SAMPLE_RATE = 16000
NOISE_THRESHOLD = 0.005

# Keep the noise filtering functions unchanged
def butter_highpass(cutoff, fs, order=5):
    """Design a highpass filter"""
    logger.debug(f"Designing highpass filter: cutoff={cutoff}, fs={fs}, order={order}")
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="highpass", analog=False)
    return b, a

def apply_noise_filter(audio_data, cutoff=100):
    """Apply noise filtering to audio data"""
    logger.debug("Applying noise filter to audio data")
    b, a = butter_highpass(cutoff, SAMPLE_RATE)
    filtered_audio = filtfilt(b, a, audio_data)
    filtered_audio[abs(filtered_audio) < NOISE_THRESHOLD] = 0
    return filtered_audio

def record_audio(duration=5):
    """Record audio from microphone with noise filtering"""
    logger.info(f"Recording audio for {duration} seconds")
    recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()
    audio_data = recording.flatten()
    filtered_audio = apply_noise_filter(audio_data)
    return filtered_audio

def transcribe_audio(audio_chunk, pipe):
    """Transcribe a single audio chunk using pipeline"""
    logger.debug("Processing audio chunk for transcription")
    try:
        # Create a dict with the required format for the pipeline
        audio_dict = {"array": audio_chunk, "sampling_rate": SAMPLE_RATE}
        result = pipe(audio_dict, batch_size=8, return_timestamps=True)
        transcription = result["chunks"][0]["text"] if result["chunks"] else ""
        logger.info("Successfully transcribed audio chunk")
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
    if "recording" not in st.session_state:
        st.session_state.recording = False

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

    if st.button("Record" if not st.session_state.recording else "Stop"):
        st.session_state.recording = not st.session_state.recording
        logger.info(f"Recording state changed to: {st.session_state.recording}")

    status_placeholder = st.empty()
    transcription_placeholder = st.empty()

    while st.session_state.recording:
        status_placeholder.markdown("🔴 Recording...")

        audio_chunk = record_audio(duration=5)
        text = transcribe_audio(audio_chunk, pipe)

        timestamp = time.strftime("%H:%M:%S")
        st.session_state.transcriptions.append(f"{text}")
        logger.debug(f"Added transcription at {timestamp}: {text}")

        transcription_placeholder.markdown("".join(st.session_state.transcriptions))
        time.sleep(0.1)

    status_placeholder.markdown("⚪ Not Recording")

    if st.session_state.transcriptions:
        transcription_placeholder.markdown("".join(st.session_state.transcriptions))

    if st.button("Clear Transcriptions"):
        logger.info("Clearing transcription history")
        st.session_state.transcriptions = []
        transcription_placeholder.empty()

main()
