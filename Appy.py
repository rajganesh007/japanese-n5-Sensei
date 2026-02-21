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
    st.header("Settings")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")
    st.divider()
    dev_mode = st.checkbox("🚀 Mock Mode (No API calls)", value=False)
    
    if st.button("Hard Reset App"):
        st.session_state.clear()
        st.rerun()

# 4. Helpers
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        return [p.extract_text() for p in reader.pages if p.extract_text()]
    except: return []

def play_audio(text):
    js_code = f"<script>window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance('{text.replace("'", "\\'")}'); msg.lang = 'ja-JP'; window.speechSynthesis.speak(msg);</script>"
    components.html(js_code, height=0)

def call_gemini_smart(client, contents):
    # Standardizing to stable 2026 model IDs
    for model_id in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except Exception as e:
            if "404" in str(e): continue
            if "429" in str(e):
                st.warning("Quota limit reached. Auto-waiting 20s...")
                time.sleep(20)
                return client.models.generate_content(model=model_id, contents=contents)
            raise e

# 5. Main Logic
if (st.session_state.api_key or dev_mode) and (uploaded_file or dev_mode):
    client = None if dev_mode else genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    pages = get_pdf_text(uploaded_file) if uploaded_file else ["Mock Data"]

    # --- SCREEN 1: Ask Question (Only if no question active) ---
    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!", type="primary"):
            if dev_mode:
                st.session_state.current_question = "Japanese: 昨日の天気はどうでしたか？\nRomaji: Kinou no tenki wa dou deshita ka?"
                st.rerun()
            else:
                with st.spinner("Sensei is picking a topic..."):
                    try:
                        random_page = random.choice(pages) if pages else "N5 Vocabulary"
                        prompt = (
                            f"Context: {random_page[:1500]}\n"
                            "Task: Ask ONE N5 Japanese question. NO ENGLISH.\n"
                            "Format: Japanese: [text]\nRomaji: [text]"
                        )
                        response = call_gemini_smart(client, prompt)
                        st.session_state.current_question = response.text
                        st.rerun()
                    except Exception as e: st.error(e)

    # --- SCREEN 2: Question & Audio Input ---
    else:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            play_audio(match.group(1) if match else st.session_state.current_question)

        st.divider()
        
        # Audio input remains until "Next Question" is pressed
        student_audio = st.audio_input("Record response", key=f"voice_{st.session_state.question_count}")

        # Only show "Submit" if feedback hasn't been generated yet
        if student_audio and not st.session_state.feedback:
            if st.button("Submit Answer", type="secondary"):
                if dev_mode:
                    st.session_state.feedback = "Japanese: とてもいいですね！\nRomaji: Totemo ii desu ne!"
                    st.rerun()
                else:
                    with st.spinner("Sensei is listening..."):
                        try:
                            fb_prompt = [
                                f"Question: {st.session_state.current_question}. Evaluate my response. NO ENGLISH. Format: Japanese: [text]\nRomaji: [text]",
                                types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                            ]
                            response = call_gemini_smart(client, fb_prompt)
                            st.session_state.feedback = response.text
                            st.rerun()
                        except Exception as e: st.error(e)

        # --- SCREEN 3: Feedback & NEXT BUTTON (Permanent until Reset) ---
        if st.session_state.feedback:
            st.success("Sensei's Feedback:")
            st.write(st.session_state.feedback)
            
            # Using a container to ensure these buttons stay grouped and visible
            with st.container():
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    if st.button("🔈 Hear Feedback"):
                        match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
                        play_audio(match.group(1) if match else st.session_state.feedback)
                with f_col2:
                    # Next Question Button - Using the callback ensures a clean wipe
                    st.button("Next Question ➔", on_click=reset_session, type="primary")

else:
    st.warning("Please enter your API Key and upload a PDF, or enable Mock Mode.")
