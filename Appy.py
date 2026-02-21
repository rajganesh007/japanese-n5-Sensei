import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re
import time # Added for sleep
import streamlit.components.v1 as components

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# --- State Management ---
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""
if 'feedback' not in st.session_state: st.session_state.feedback = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

# --- Robust PDF Reader ---
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        raw_text = "".join([p.extract_text() for p in reader.pages[:5]])
        return re.sub(r'\s+', ' ', raw_text)
    except: return ""

# --- Quota-Friendly Voice ---
def play_audio(text, slow=True):
    rate = 0.6 if slow else 1.0
    safe_text = text.replace("'", "\\'")
    js_code = f"<script>var msg = new SpeechSynthesisUtterance('{safe_text}'); msg.lang = 'ja-JP'; msg.rate = {rate}; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

# --- Smart Retry Wrapper (The Fix) ---
def call_gemini_with_retry(client, model, contents, max_retries=3):
    for i in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if "429" in str(e) and i < max_retries - 1:
                wait_time = 20  # Wait 20 seconds as per your error message
                st.warning(f"Quota reached. Sensei is resting for {wait_time}s... (Attempt {i+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise e

# --- Main App ---
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key)
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            try:
                prompt = f"Context: {vocab_text[:1200]}\nTask: Ask an N5 Japanese question. NO ENGLISH.\nFormat: Japanese: [text]\nRomaji: [text]"
                # Using the retry wrapper
                response = call_gemini_with_retry(client, 'gemini-2.0-flash', prompt)
                st.session_state.current_question = response.text
                st.session_state.feedback = ""
                st.rerun()
            except Exception as e:
                st.error(f"Sensei is exhausted: {e}")

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            play_audio(match.group(1) if match else st.session_state.current_question)

        st.divider()
        student_audio = st.audio_input("Record response")

        if student_audio and st.button("Submit Answer"):
            with st.spinner("Analyzing..."):
                try:
                    fb_prompt = [
                        f"Question: {st.session_state.current_question}. Evaluate student audio. NO ENGLISH. Format: Japanese: [text]\nRomaji: [text]",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                    # Using the retry wrapper
                    response = call_gemini_with_retry(client, 'gemini-2.0-flash', fb_prompt)
                    st.session_state.feedback = response.text
                except Exception as e:
                    st.error(f"Analysis Error: {e}")

    if st.session_state.feedback:
        st.success(st.session_state.feedback)
        if st.button("🔈 Hear Feedback"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
            play_audio(match.group(1) if match else st.session_state.feedback)
