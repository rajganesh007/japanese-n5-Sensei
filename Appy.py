import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re
import time
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# 2. State Management & Reset Logic
def reset_session():
    """Clears question and feedback to start fresh."""
    st.session_state.current_question = ""
    st.session_state.feedback = ""

if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""
if 'feedback' not in st.session_state: st.session_state.feedback = ""

# 3. Sidebar Setup
with st.sidebar:
    st.header("Setup & Dev Tools")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
    st.divider()
    dev_mode = st.checkbox("Mock Mode (Save Quota)", value=False)
    if st.button("Reset App Entirely"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# 4. Helper: PDF Text Extraction
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        raw_text = "".join([p.extract_text() for p in reader.pages[:5]])
        return re.sub(r'\s+', ' ', raw_text)
    except Exception: return ""

# 5. Helper: Voice Playback
def play_audio(text, slow=True):
    rate = 0.6 if slow else 1.0
    safe_text = text.replace("'", "\\'").replace("\n", " ")
    js_code = f"<script>window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance('{safe_text}'); msg.lang = 'ja-JP'; msg.rate = {rate}; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

# 6. Helper: Smart Model Caller
def call_gemini_smart(client, contents):
    # Standardized 2026 stable IDs
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']
    for model_id in models_to_try:
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except Exception as e:
            if "404" in str(e): continue
            if "429" in str(e):
                st.warning("Quota hit. Auto-waiting 20s...")
                time.sleep(20)
                return client.models.generate_content(model=model_id, contents=contents)
            raise e
    raise Exception("Model not found. Check AI Studio for available models.")

# 7. Main Application Logic
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    vocab_text = get_pdf_text(uploaded_file)

    # --- Step 1: Generate Question ---
    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!"):
            if dev_mode:
                st.session_state.current_question = "Japanese: 今日は何曜日ですか？\nRomaji: Kyou wa nan-youbi desu ka?"
                st.rerun()
            else:
                with st.spinner("Thinking..."):
                    try:
                        prompt = f"Context: {vocab_text[:1200]}\nTask: Ask an N5 Japanese question. NO ENGLISH.\nFormat: Japanese: [text]\nRomaji: [text]"
                        response = call_gemini_smart(client, prompt)
                        st.session_state.current_question = response.text
                        st.rerun()
                    except Exception as e: st.error(e)
    
    # --- Step 2: Display & Interaction ---
    else:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            play_audio(match.group(1) if match else st.session_state.current_question)

        st.divider()
        student_audio = st.audio_input("Record your response")

        if student_audio and not st.session_state.feedback:
            if st.button("Submit Answer"):
                if dev_mode:
                    st.session_state.feedback = "Japanese: すばらしいです！\nRomaji: Subarashii desu!"
                    st.rerun()
                else:
                    with st.spinner("Analyzing..."):
                        try:
                            fb_prompt = [
                                f"Question: {st.session_state.current_question}. Evaluate student audio. NO ENGLISH. Format: Japanese: [text]\nRomaji: [text]",
                                types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                            ]
                            response = call_gemini_smart(client, fb_prompt)
                            st.session_state.feedback = response.text
                            st.rerun()
                        except Exception as e: st.error(e)

        # --- Step 3: Feedback & Next ---
        if st.session_state.feedback:
            st.success(st.session_state.feedback)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔈 Hear Feedback"):
                    match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
                    play_audio(match.group(1) if match else st.session_state.feedback)
            with col2:
                # The Reset Button
                st.button("Next Question ➔", on_click=reset_session, type="primary")
