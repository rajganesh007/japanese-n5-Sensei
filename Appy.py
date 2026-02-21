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
    """Clears state and increments counter to force a fresh UI and new AI context."""
    st.session_state.current_question = ""
    st.session_state.feedback = ""
    st.session_state.question_count += 1

# 3. Sidebar
with st.sidebar:
    st.header("Settings")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
    dev_mode = st.checkbox("🚀 Mock Mode (No API calls)", value=False)
    if st.button("Hard Reset App"):
        st.session_state.clear()
        st.rerun()

# 4. Helpers
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        # Store as a list of pages to allow random selection
        return [p.extract_text() for p in reader.pages if p.extract_text() and len(p.extract_text()) > 100]
    except: return []

def play_audio(text):
    # Regex to find Japanese characters only
    jap_match = re.search(r"Japanese:\s*(.*)", text)
    speech_text = jap_match.group(1) if jap_match else text
    safe_text = speech_text.split('\n')[0].replace("'", "\\'").replace('"', '\\"')
    js_code = f"<script>window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance('{safe_text}'); msg.lang = 'ja-JP'; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

def call_gemini_smart(client, contents):
    for model_id in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except Exception as e:
            if "404" in str(e): continue
            if "429" in str(e):
                time.sleep(20)
                return client.models.generate_content(model=model_id, contents=contents)
            raise e

# 5. Main Logic
if (st.session_state.api_key or dev_mode) and (uploaded_file or dev_mode):
    client = None if dev_mode else genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    all_pages = get_pdf_text(uploaded_file) if uploaded_file else ["Mock Context"]

    # --- SCREEN 1: Ask Question ---
    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!", type="primary"):
            if dev_mode:
                st.session_state.current_question = "Japanese: どこに住んでいますか？\nRomaji: Doko ni sunde imasu ka?\nEnglish: Where do you live?"
                st.rerun()
            else:
                with st.spinner("Sensei is flipping pages..."):
                    # REPETITION FIX: Pick a random page so the context is never the same
                    random_context = random.choice(all_pages) if all_pages else "N5 Grammar"
                    prompt = (
                        f"Context: {random_context[:1000]}\n"
                        f"Random Salt: {random.random()}\n"
                        "Task: Ask a unique N5 Japanese question based on the context. "
                        "You MUST provide the response in THREE lines: Japanese, Romaji, and English.\n"
                        "Format:\nJapanese: [text]\nRomaji: [text]\n
