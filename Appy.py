import streamlit as st
from google import genai
from google.genai import types
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

def play_audio(client, text, slow=True):
    """Helper to generate and play audio from text."""
    try:
        speed = "very slowly" if slow else "naturally"
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash-tts',
            contents=f"Say this {speed} in Japanese: {text}",
            config=types.GenerateContentConfig(response_modalities=['AUDIO'])
        )
        for part in audio_res.candidates[0].content.parts:
            if part.inline_data:
                st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
    except Exception:
        st.warning("Audio playback failed, but here is the text!")

if st.session_state.api_key and uploaded_file:
    client = genai.Client(api_key=st.session_state.api_key, http_options={'api_version': 'v1'})
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            txt_prompt = f"Using this vocab: {vocab_text[:2000]}. Ask a short N5 Japanese question. Provide: Japanese, Romaji, and English."
            response = client.models.generate_content(model='gemini-2.5-flash', contents=txt_prompt)
            st.session_state.current_question = response.text
            st.rerun()

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        if st.button("🔈 Hear Question"):
            jap_line = st.session_state.current_question.split('\n')[0].replace('Japanese:', '').strip()
            play_audio(client, jap_line)

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record your response")

    if student_audio:
        with st.spinner("Sensei is listening and preparing feedback..."):
            try:
                # 1. Generate Feedback Text
                feedback_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        f"Question: {st.session_state.current_question}. Correct the student's Japanese. Give feedback in Japanese and Romaji.",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                )
                feedback_text = feedback_res.text
                st.success("Sensei says:")
                st.write(feedback_text)
                
                # 2. NEW: Generate Feedback Audio
                # We extract the first line (usually the Japanese correction) for audio
                feedback_jap = feedback_text.split('\n')[0].strip()
                play_audio(client, feedback_jap, slow=False)
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
else:
    st.info("Please set up the sidebar to begin.")
