import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re
import time
import random # Added for variety
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# 2. State Management
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""
if 'feedback' not in st.session_state: st.session_state.feedback = ""
if 'question_count' not in st.session_state: st.session_state.question_count = 0

def reset_session():
    """Clears state and increments a counter to force widget resets."""
    st.session_state.current_question = ""
    st.session_state.feedback = ""
    st.session_state.question_count += 1 # Forces audio_input to reset

# 3. Sidebar
with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
    dev_mode = st.checkbox("Mock Mode (Save Quota)", value=False)

# 4. Helpers
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        return "".join([p.extract_text() for p in reader.pages[:10]]) # Increased range
    except: return ""

def play_audio(text):
    js_code = f"<script>window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance('{text.replace("'", "\\'")}'); msg.lang = 'ja-JP'; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

def call_gemini_smart(client, contents):
    for model_id in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except Exception as e:
            if "404" in str(e): continue
            raise e

# 7. Main Logic
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    vocab_text = get_pdf_text(uploaded_file)

    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!"):
            with st.spinner("Thinking..."):
                # VARIETY FIX: Add a random seed and instruction to pick a unique topic
                seed = random.randint(1, 1000)
                prompt = (
                    f"Context: {vocab_text}\n"
                    f"Random Seed: {seed}\n"
                    "Task: Pick a RANDOM vocabulary word or grammar point from the context and ask a question. "
                    "Ensure this question is different from common basic greetings. NO ENGLISH. "
                    "Format: Japanese: [text]\nRomaji: [text]"
                )
                response = call_gemini_smart(client, prompt)
                st.session_state.current_question = response.text
                st.rerun()
    
    else:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            play_audio(match.group(1) if match else st.session_state.current_question)

        st.divider()
        
        # KEY FIX: The key includes 'question_count' so it resets every time you hit Next
        student_audio = st.audio_input("Record response", key=f"audio_{st.session_state.question_count}")

        if student_audio and not st.session_state.feedback:
            if st.button("Submit Answer"):
                with st.spinner("Analyzing..."):
                    fb_prompt = [
                        f"Question: {st.session_state.current_question}. Evaluate student audio. NO ENGLISH. Format: Japanese: [text]\nRomaji: [text]",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                    response = call_gemini_smart(client, fb_prompt)
                    st.session_state.feedback = response.text
                    st.rerun()

        if st.session_state.feedback:
            st.success(st.session_state.feedback)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔈 Hear Feedback"):
                    match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
                    play_audio(match.group(1) if match else st.session_state.feedback)
            with col2:
                # RESET FIX: Calls reset_session which clears text AND changes the audio widget key
                st.button("Next Question ➔", on_click=reset_session, type="primary")
