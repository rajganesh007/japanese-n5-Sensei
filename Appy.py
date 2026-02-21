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

# 2. State Management
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

# 4. Helper: PDF Text Extraction
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        raw_text = "".join([p.extract_text() for p in reader.pages[:5]])
        return re.sub(r'\s+', ' ', raw_text)
    except Exception:
        return ""

# 5. Helper: Voice Playback (Browser API)
def play_audio(text, slow=True):
    rate = 0.6 if slow else 1.0
    safe_text = text.replace("'", "\\'").replace("\n", " ")
    js_code = f"""
    <script>
    window.speechSynthesis.cancel();
    var msg = new SpeechSynthesisUtterance('{safe_text}');
    msg.lang = 'ja-JP';
    msg.rate = {rate};
    window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

# 6. Helper: API Retry Logic (Handles 429 Errors)
def call_gemini_with_retry(client, model, contents, max_retries=3):
    for i in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if "429" in str(e) and i < max_retries - 1:
                wait_time = 20 
                st.warning(f"Quota reached. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise e

# 7. Main Application Logic
if st.session_state.api_key and uploaded_file:
    # Initialize client
    client = genai.Client(api_key=st.session_state.api_key)
    vocab_text = get_pdf_text(uploaded_file)
    
    # 2026 Stable Model String
    MODEL_ID = 'gemini-1.5-flash' 

    # --- Section: Question Generation ---
    if st.button("Sensei, ask me a question!"):
        if dev_mode:
            st.session_state.current_question = "Japanese: これはなんですか？\nRomaji: Kore wa nan desu ka?"
            st.session_state.feedback = ""
            st.rerun()
        elif not vocab_text:
            st.error("Could not read PDF content.")
        else:
            with st.spinner("Sensei is writing..."):
                try:
                    txt_prompt = (
                        f"Context: {vocab_text[:1200]}\n\n"
                        "Task: Ask an N5 Japanese question. NO ENGLISH.\n"
                        "Format exactly as:\nJapanese: [text]\nRomaji: [text]"
                    )
                    # Use the stable model ID
                    response = call_gemini_with_retry(client, MODEL_ID, txt_prompt)
                    st.session_state.current_question = response.text
                    st.session_state.feedback = ""
                    st.rerun()
                except Exception as e:
                    # If 1.5-flash still fails, try the newer versioning
                    st.error(f"Model Error. Try replacing MODEL_ID with 'gemini-1.5-flash-8b' or check API settings.")
                    st.error(f"Details: {str(e)}")

    # --- Section: Question Display & Voice ---
    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            match = re.search(r"Japanese:\s*(.*)", st.session_state.current_question)
            jap_line = match.group(1) if match else st.session_state.current_question.split('\n')[0]
            play_audio(jap_line, slow=True)

        st.divider()
        st.subheader("Your Answer")
        student_audio = st.audio_input("Record your response")

        if student_audio:
            if st.button("Evaluate My Answer"):
                if dev_mode:
                    st.session_state.feedback = "Japanese: よくできました。\nRomaji: Yoku dekimashita."
                else:
                    with st.spinner("Sensei is listening..."):
                        try:
                            fb_prompt = [
                                (f"Question: {st.session_state.current_question}. "
                                 "Evaluate student audio response. NO ENGLISH. "
                                 "Format:\nJapanese: [feedback]\nRomaji: [feedback]"),
                                types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                            ]
                            response = call_gemini_with_retry(client, MODEL_ID, fb_prompt)
                            st.session_state.feedback = response.text
                        except Exception as e:
                            st.error(f"Analysis Error: {e}")

    # --- Section: Feedback Display ---
    if st.session_state.feedback:
        st.success("Feedback:")
        st.write(st.session_state.feedback)
        if st.button("🔈 Hear Feedback"):
            fb_match = re.search(r"Japanese:\s*(.*)", st.session_state.feedback)
            fb_text = fb_match.group(1) if fb_match else st.session_state.feedback.split('\n')[0]
            play_audio(fb_text, slow=False)
