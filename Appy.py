import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter Gemini API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    return "".join([p.extract_text() for p in reader.pages[:10]])

if st.session_state.api_key and uploaded_file:
    genai.configure(api_key=st.session_state.api_key)
    
    # Using the universal stable model for 2026
    # If this still gives an error, try 'gemini-1.5-flash' as a fallback
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            # We combine text and audio requests into one simpler flow
            prompt = f"""
            Using this vocab: {vocab_text[:2000]}
            1. Ask a short N5 Japanese question. 
            2. Provide only the text for now.
            """
            res = model.generate_content(prompt)
            st.session_state.current_question = res.text
            
            # For the voice, we will use a separate 'Speech' request 
            # or simply rely on the text for the student to read for a moment 
            # while the TTS endpoint stabilizes.
            st.rerun()

    if st.session_state.current_question:
        st.info(f"Sensei asks: {st.session_state.current_question}")
        
        # New 2026 'Listen' feature:
        if st.button("🔈 Hear Question (Slow Pace)"):
            with st.spinner("Generating audio..."):
                # We use the specific preview-tts model name which is active this month
                tts_model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
                audio_prompt = f"Speak this slowly and clearly in Japanese: {st.session_state.current_question}"
                audio_res = tts_model.generate_content(audio_prompt)
                if hasattr(audio_res, 'audio_content'):
                    st.audio(audio_res.audio_content, format="audio/wav")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Respond to Sensei:")

    if student_audio:
        with st.spinner("Analyzing..."):
            feedback_prompt = f"The student is responding to: {st.session_state.current_question}. Correct their N5 Japanese."
            feedback_res = model.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Waiting for API Key and PDF.")
