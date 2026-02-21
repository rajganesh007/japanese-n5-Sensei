import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# Memory management
if 'api_key' not in st.session_state: st.session_state.api_key = ""
if 'current_question' not in st.session_state: st.session_state.current_question = ""

with st.sidebar:
    st.header("Setup")
    st.session_state.api_key = st.text_input("Enter API Key:", value=st.session_state.api_key, type="password")
    uploaded_file = st.file_uploader("Upload N5 PDF", type="pdf")

@st.cache_data
def get_pdf_text(file_buffer):
    reader = PdfReader(file_buffer)
    return "".join([p.extract_text() for p in reader.pages[:10]])

if st.session_state.api_key and uploaded_file:
    genai.configure(api_key=st.session_state.api_key)
    # Using 2026 stable models
    model_tts = genai.GenerativeModel('gemini-2.5-flash-tts')
    model_chat = genai.GenerativeModel('gemini-2.5-flash')
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is speaking..."):
            # Step 1: Pick a question
            txt_prompt = f"Using this vocab: {vocab_text[:2000]}, ask me a short N5 Japanese question."
            txt_res = model_chat.generate_content(txt_prompt)
            st.session_state.current_question = txt_res.text
            
            # Step 2: Speak slowly
            # Use specific pace markers for the 2.5 TTS model
            audio_prompt = f"Say this at a [slow and clear] pace: {st.session_state.current_question}"
            audio_res = model_tts.generate_content(audio_prompt)
            
            # Check for audio content and play it
            if hasattr(audio_res, 'audio_content'):
                st.audio(audio_res.audio_content, format="audio/wav", autoplay=True)

    if st.session_state.current_question:
        st.info(f"Question: {st.session_state.current_question}")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Respond to Sensei:")

    if student_audio:
        with st.spinner("Analyzing..."):
            feedback_prompt = f"The student answered: {st.session_state.current_question}. Analyze their audio for N5 accuracy."
            feedback_res = model_chat.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Waiting for API Key and PDF.")
