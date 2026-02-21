import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import time

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# --- Memory Setup ---
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    return "".join([p.extract_text() for p in reader.pages[:10]]) # First 10 pages for speed

# --- The App Logic ---
if st.session_state.api_key and uploaded_file:
    genai.configure(api_key=st.session_state.api_key)
    
    # We use the TTS (Text-To-Speech) model variant for 2026
    model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
    vocab_text = get_pdf_text(uploaded_file)

    # 1. BUTTON: Ask a New Question
    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            prompt = f"Using this vocab: {vocab_text[:3000]}, ask me a simple N5 Japanese question. Speak clearly."
            # Generate Audio Response
            response = model.generate_content(prompt, config={'response_modalities': ['AUDIO']})
            
            # Extract and play audio
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            st.session_state.current_question = response.text # Save text for reference
            st.audio(audio_data, format="audio/wav", autoplay=True)
            st.info(f"Sensei asked: {st.session_state.current_question}")

    # 2. INPUT: Student Answers
    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Respond to Sensei's question:")

    if student_audio:
        with st.spinner("Analyzing your answer..."):
            # Feedback prompt
            feedback_prompt = f"""
            Context: {vocab_text[:3000]}
            Sensei's Question: {st.session_state.current_question}
            Student's Audio Answer provided.
            TASK: 
            1. Transcribe the student's answer.
            2. Give feedback: Is it grammatically correct for N5? 
            3. Provide the correct version in Japanese and English.
            """
            feedback_res = model.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Paste your key and upload your PDF to start the lesson.")
