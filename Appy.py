import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import re
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor (No English)")

# 2. State Management
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""
if 'feedback' not in st.session_state: st.session_state.feedback = ""

# 3. Sidebar Setup
with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

# 4. Helper: PDF Text Extraction
@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        raw_text = "".join([p.extract_text() for p in reader.pages[:5]])
        return re.sub(r'\s+', ' ', raw_text)
    except Exception:
        return ""

# 5. Helper: Voice Playback
def play_audio(text, slow=True):
    rate = 0.6 if slow else 1.0
    safe_text = text.replace("'", "\\'")
    js_code = f"""
    <script>
    var msg = new SpeechSynthesisUtterance('{safe_text}');
    msg.lang = 'ja-JP';
    msg.rate = {rate};
    window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

# 6. Main Application Logic
if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key)
    vocab_text = get_pdf_text(uploaded_file)

    # --- Section: Question Generation ---
    if st.button("Sensei, ask me a question!"):
        if not vocab_text:
            st.error("Could not read PDF content.")
        else:
            with st.spinner("Sensei is thinking..."):
                try:
                    # PROMPT EDIT: Strictly Japanese and Romaji only
                    txt_prompt = (
                        f"Context: {vocab_text[:1500]}\n\n"
                        "Task: Ask an N5 Japanese question. DO NOT use English.\n"
                        "Format your response exactly as:\n"
                        "Japanese: [sentence]\nRomaji: [sentence]"
                    )
                    response = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=txt_prompt
                    )
                    st.session_state.current_question = response.text
                    st.session_state.feedback = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"API Error: {str(e)}")

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
                with st.spinner("Sensei is listening..."):
                    try:
                        # PROMPT EDIT: Evaluation strictly in Japanese and Romaji
                        feedback_res = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[
                                (f"Question was: {st.session_state.current_question}. "
                                 "Evaluate student audio response. Do not use any English. "
                                 "Provide feedback using the format:\nJapanese: [feedback]\nRomaji: [feedback]"),
                                types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                            ]
                        )
                        st.session_state.feedback = feedback_res.text
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
