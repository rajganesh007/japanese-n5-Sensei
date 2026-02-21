import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

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
    
    # We use the TTS-specific model for high-quality voice
    model_tts = genai.GenerativeModel('gemini-2.5-flash-tts')
    model_chat = genai.GenerativeModel('gemini-2.5-flash')
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is preparing to speak..."):
            # Step 1: Generate the Text Question
            txt_prompt = f"Using this vocab: {vocab_text[:2000]}, create one simple N5 Japanese question."
            txt_res = model_chat.generate_content(txt_prompt)
            st.session_state.current_question = txt_res.text
            
            # Step 2: Generate the Slow Audio
            # The [slow and clear] tag is a 2026 'Director Note' for the TTS model
            audio_prompt = f"Say the following in a [slow and clear] Japanese voice: {st.session_state.current_question}"
            audio_res = model_tts.generate_content(audio_prompt)
            
            # Autoplay the audio
            if hasattr(audio_res, 'audio_content'):
                st.audio(
