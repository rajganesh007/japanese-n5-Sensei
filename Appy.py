import streamlit as st
from google import genai
from google.genai import types
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
    # NEW: 2026 Client initialization
    client = genai.Client(api_key=st.session_state.api_key)
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            # Update 1: Include Romaji and English in the output format
            txt_prompt = f"""
            Using this vocab: {vocab_text[:2000]}
            Ask a short N5 Japanese question. 
            Format:
            Japanese: [Text]
            Romaji: [Text]
            English: [Text]
            """
            response = client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=txt_prompt
            )
            st.session_state.current_question = response.text
            st.rerun()

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        
        # Update 2: Fix Audio with the correct 2026 SDK syntax
        if st.button("🔈 Hear Question (Slow Pace)"):
            with st.spinner("Generating audio..."):
                try:
                    # Extract just the Japanese line
                    japanese_text = st.session_state.current_question.split('\n')[0].replace('Japanese:', '').strip()
                    
                    audio_response = client.models.generate_content(
                        model='gemini-2.5-flash-tts',
                        contents=f"Say this very slowly and clearly: {japanese_text}",
                        config=types.GenerateContentConfig(
                            response_modalities=['AUDIO']
                        )
                    )
                    
                    # Extract audio from the new response structure
                    for part in audio_response.candidates[0].content.parts:
                        if part.inline_data:
                            st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                except Exception as e:
                    st.error(f"Audio failed. Error details: {str(e)}")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record your answer:")

    if student_audio:
        with st.spinner("Sensei is analyzing..."):
            # Using new part structure for multimodal input
            feedback_prompt = f"The student is answering: {st.session_state.current_question}. Correct their N5 Japanese."
            audio_part = types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
            
            feedback_res = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[feedback_prompt, audio_part]
            )
            st.success("Feedback:")
            st.write(feedback_res.text)
else:
    st.info("Awaiting Setup...")
