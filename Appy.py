import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="N5 Voice Sensei", page_icon="🎤")
st.title("🎤 N5 Japanese Voice Tutor")

# Persistent state
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
    
    # Standard model for text/logic
    model = genai.GenerativeModel('gemini-2.5-flash')
    # Use the Lite version for more stable voice generation in 2026
    tts_model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-tts')
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            txt_prompt = f"Pick a word from this N5 list: {vocab_text[:2000]}. Ask a simple question using it. Reply ONLY with the question text."
            res = model.generate_content(txt_prompt)
            st.session_state.current_question = res.text
            st.rerun()

    if st.session_state.current_question:
        st.info(f"Question: {st.session_state.current_question}")
        
        # Audio generation logic
        if st.button("🔈 Speak Question Slowly"):
            with st.spinner("Generating audio..."):
                try:
                    # Passing instructions directly in the prompt for TTS models
                    audio_prompt = f"Say clearly and very slowly in Japanese: {st.session_state.current_question}"
                    # Using the simpler unary call which is more stable on Streamlit
                    audio_res = tts_model.generate_content(audio_prompt)
                    
                    if hasattr(audio_res, 'audio_content'):
                        st.audio(audio_res.audio_content, format="audio/wav", autoplay=True)
                except Exception as e:
                    st.error("Audio failed. Try the text version for now.")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record your answer:")

    if student_audio:
        with st.spinner("Sensei is analyzing..."):
            feedback_prompt = f"The student is answering: {st.session_state.current_question}. Give feedback in English and Japanese."
            feedback_res = model.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Awaiting Setup...")
