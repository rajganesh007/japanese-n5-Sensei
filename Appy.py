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

if st.session_state.api_key and uploaded_file:
    # Initialize client with stable v1 API
    client = genai.Client(
        api_key=st.session_state.api_key,
        http_options={'api_version': 'v1'}
    )
    vocab_text = get_pdf_text(uploaded_file)

    if st.button("Sensei, ask me a question!"):
        with st.spinner("Sensei is thinking..."):
            txt_prompt = f"Using this vocab: {vocab_text[:2000]}. Ask a short N5 Japanese question. Include Romaji and English translation."
            try:
                # SWITCHED to 2.5 Flash (The 2026 Free Tier Workhorse)
                response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=txt_prompt
                )
                st.session_state.current_question = response.text
                st.rerun()
            except Exception as e:
                st.error(f"Quota Error: {str(e)}")

    if st.session_state.current_question:
        st.info(st.session_state.current_question)
        
        if st.button("🔈 Hear Question"):
            with st.spinner("Generating audio..."):
                try:
                    jap_line = st.session_state.current_question.split('\n')[0].replace('Japanese:', '').strip()
                    
                    # SWITCHED to 2.5 Flash Lite TTS for maximum free stability
                    audio_res = client.models.generate_content(
                        model='gemini-2.5-flash-lite-preview-tts',
                        contents=f"Say this very slowly: {jap_line}",
                        config=types.GenerateContentConfig(response_modalities=['AUDIO'])
                    )
                    
                    for part in audio_res.candidates[0].content.parts:
                        if part.inline_data:
                            st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                except Exception as e:
                    st.error("Audio limit reached. Try again in a minute.")

    st.divider()
    st.subheader("Your Answer")
    student_audio = st.audio_input("Record your response")

    if student_audio:
        with st.spinner("Analyzing..."):
            try:
                # Using 2.5 Flash for multimodal analysis
                feedback_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        f"Question: {st.session_state.current_question}. Correct the student's Japanese.",
                        types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                    ]
                )
                st.success("Feedback:")
                st.write(feedback_res.text)
            except Exception as e:
                st.error(f"Analysis Error: {str(e)}")
else:
    st.info("Please set up the sidebar to begin.")
