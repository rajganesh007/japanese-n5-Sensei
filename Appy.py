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
        return [p.extract_text() for p in reader.pages if p.extract_text()]
    except: return []

def play_audio(text):
    jap_match = re.search(r"Japanese:\s*(.*)", text)
    speech_text = jap_match.group(1) if jap_match else text
    safe_text = speech_text.replace("'", "\\'").replace("\n", " ")
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
    all_pages = get_pdf_text(uploaded_file) if uploaded_file else ["Mock Data"]

    if not st.session_state.current_question:
        if st.button("Sensei, ask me a question!", type="primary"):
            if dev_mode:
                st.session_state.current_question = "Japanese: あなたの趣味は何ですか？\nRomaji: Anata no shumi wa nan desu ka?\nEnglish: What is your hobby?"
                st.rerun()
            else:
                with st.spinner("Sensei is searching..."):
                    context_slice = random.choice(all_pages) if all_pages else "N5 Vocabulary"
                    prompt = (
                        f"Context: {context_slice[:1500]}\n"
                        "Task: Ask ONE specific N5 Japanese question. Include English meaning.\n"
                        "Format:\nJapanese: [sentence]\nRomaji: [sentence]\nEnglish: [meaning]"
                    )
                    response = call_gemini_smart(client, prompt)
                    st.session_state.current_question = response.text
                    st.rerun()

    else:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            play_audio(st.session_state.current_question)

        st.divider()
        student_audio = st.audio_input("Record response", key=f"v_{st.session_state.question_count}")

        if student_audio and not st.session_state.feedback:
            if st.button("Submit Answer"):
                if dev_mode:
                    # MOCK CHANGE: Now returns a correction so you can test the UI flow
                    st.session_state.feedback = "Japanese: 残念ですが、違います。趣味について答えてください。\nRomaji: Zannen desu ga, chigaimasu. Shumi ni tsuite kotaete kudasai."
                    st.rerun()
                else:
                    with st.spinner("Sensei is checking logic..."):
                        # THE "HONEST SENSEI" PROMPT
                        fb_prompt = [
                            f"Question Asked: {st.session_state.current_question}\n"
                            "STRICT EVALUATION TASK:\n"
                            "1. If the student's answer is logically incorrect (e.g., they said 'apple' when asked for 'hobby'), you MUST say it is wrong.\n"
                            "2. Be a polite but honest Japanese teacher. Correct them if the context is wrong.\n"
                            "3. Do NOT say 'Good' or 'Totemo ii' unless they actually answered the question correctly.\n"
                            "Format: Japanese: [polite correction]\nRomaji: [polite correction]",
                            types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                        ]
                        response = call_gemini_smart(client, fb_prompt)
                        st.session_state.feedback = response.text
                        st.rerun()

        if st.session_state.feedback:
            st.success("Sensei's Feedback:")
            st.write(st.session_state.feedback)
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                if st.button("🔈 Hear Feedback"):
                    play_audio(st.session_state.feedback)
            with f_col2:
                st.button("Next Question ➔", on_click=reset_session, type="primary")
