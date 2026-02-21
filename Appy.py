import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re
import time
import random
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
    """Clears state to trigger the 'Ask a Question' screen again."""
    st.session_state.current_question = ""
    st.session_state.feedback = ""
    st.session_state.question_count += 1

# 3. Sidebar
with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
    if st.button("Hard Reset App"):
        st.session_state.clear()
        st.rerun()

# 4. Helpers
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        # Extract more pages for better variety
        return [p.extract_text() for p in reader.pages if p.extract_text()]
    except: return []

def play_audio(text):
    js_code = f"<script>window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance('{text.replace("'", "\\'")}'); msg.lang = 'ja-JP'; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

def call_gemini_smart(client, contents):
    for model_id in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except Exception as e:
            if "404" in str(e): continue
            if "429" in str(e):
                st.warning("Quota reached. Waiting 20s...")
                time.sleep(20)
                return client.models.generate_content(model=model_id, contents=contents)
            raise e

# 5. Main Logic
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    pages = get_pdf_text(uploaded_file)

    # --- SCREEN 1: Ask Question ---
    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!", type="primary"):
            with st.spinner("Sensei is picking a topic..."):
                # VARIETY FIX: Pick a random page from the PDF to use as context
                random_page = random.choice(pages) if pages else "Common N5 vocabulary"
                prompt = (
                    f"Context from PDF: {random_page[:1500]}\n"
                    "Task: Ask ONE N5 Japanese question based on this context. Be creative. "
                    "Format: Japanese: [text]\nRomaji: [text]"
                )
                response = call_gemini_smart(client, prompt)
                st.session_state.current_question = response.text
                st.rerun()

    # --- SCREEN 2: Practice & Feedback ---
    else:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            play_audio(match.group(1) if match else st.session_state.current_question)

        st.divider()
        
        # We use the question_count to ensure the audio widget resets every time
        student_audio = st.audio_input("Record response", key=f"voice_{st.session_state.question_count}")

        if student_audio and not st.session_state.feedback:
            if st.button("Submit Answer"):
                with st.spinner("Sensei is listening..."):
                    fb_prompt = [
                        f"Question: {st.session_state.current_question}. Evaluate my Japanese pronunciation and grammar. Format: Japanese: [text]\nRomaji: [text]",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                    response = call_gemini_smart(client, fb_prompt)
                    st.session_state.feedback = response.text
                    st.rerun()

        # PERSISTENCE FIX: This block stays visible even if you click other buttons
        if st.session_state.feedback:
            st.success("Sensei's Feedback:")
            st.write(st.session_state.feedback)
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                if st.button("🔈 Hear Feedback"):
                    match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
                    play_audio(match.group(1) if match else st.session_state.feedback)
            with f_col2:
                # This button clears everything and brings you back to SCREEN 1
                st.button("Next Question ➔", on_click=reset_session, type="primary")
