import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# --- Persistent Memory ---
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter Gemini API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    try:
        reader = PdfReader(file_buffer)
        return "".join([p.extract_text() for p in reader.pages[:10]])
    except:
        return ""

# --- Main App Logic ---
if st.session_state.api_key and uploaded_file:
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    vocab_text = get_pdf_text(uploaded_file)

    # 1. AI ASKS A QUESTION
    if st.button("Sensei, ask me a question!"):
        with st.spinner("Generating question..."):
            # We ask for text first to ensure stability
            prompt = f"Using this vocab context: {vocab_text[:2000]}, ask me one short N5 Japanese question. Provide the Japanese, the Romaji, and the English translation."
            response = model.generate_content(prompt)
            st.session_state.current_question = response.text
            
    if st.session_state.current_question:
        st.info(st.session_state.current_question)

    # 2. STUDENT ANSWERS
    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Click to record your answer")

    if student_audio:
        with st.spinner("Sensei is checking..."):
            feedback_prompt = f"""
            The student is answering this question: {st.session_state.current_question}
            Analyze the student's audio for N5 Japanese grammar and pronunciation.
            Give feedback in English and provide the correct Japanese way to say it.
            """
            feedback_res = model.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback from Sensei:")
            st.markdown(feedback_res.text)
else:
    st.info("Please enter your API Key and upload your PDF in the sidebar to begin.")
