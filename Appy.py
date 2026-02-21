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
    
    # 2026 Stable Models
    model_chat = genai.GenerativeModel('gemini-2.5-flash')
    model_tts = genai.GenerativeModel('gemini-2.5-flash-tts')
    
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            # Update 1: Prompts now strictly require Romaji
            txt_prompt = f"""
            Using this vocab: {vocab_text[:2000]}
            Ask a short N5 Japanese question. 
            Format your response EXACTLY like this:
            Japanese: [Japanese text]
            Romaji: [Romaji version]
            English: [English translation]
            """
            res = model_chat.generate_content(txt_prompt)
            st.session_state.current_question = res.text
            st.rerun()

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        
        # Update 2: Fix Audio Failed error with explicit modalities
        if st.button("🔈 Hear Question (Slow Pace)"):
            with st.spinner("Generating audio..."):
                try:
                    # We strip just the Japanese line for the audio
                    japanese_only = st.session_state.current_question.split('\n')[0].replace('Japanese:', '').strip()
                    audio_prompt = f"Say this very slowly and clearly in Japanese: {japanese_only}"
                    
                    # Fix: Explicitly request AUDIO modality to prevent InvalidArgument errors
                    audio_res = model_tts.generate_content(
                        audio_prompt,
                        config={'response_modalities': ['AUDIO']}
                    )
                    
                    # Access audio via the correct part attribute
                    audio_data = audio_res.candidates[0].content.parts[0].inline_data.data
                    st.audio(audio_data, format="audio/wav", autoplay=True)
                except Exception as e:
                    st.error(f"Audio failed: {str(e)}")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Respond to Sensei:")

    if student_audio:
        with st.spinner("Analyzing..."):
            feedback_prompt = f"The student is responding to: {st.session_state.current_question}. Correct their N5 Japanese and provide Romaji for your feedback."
            feedback_res = model_chat.generate_content([feedback_prompt, {"mime_type": "audio/wav", "data": student_audio.read()}])
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Awaiting Setup...")
