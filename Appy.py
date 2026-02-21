import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Setup Page Title
st.set_page_config(page_title="N5 Japanese Coach", page_icon="🇯🇵")
st.title("🏮 N5 Japanese Conversation Coach")

# 2. Sidebar for Configuration
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Google Gemini API Key:", type="password")
    uploaded_file = st.file_uploader("Upload your N5 Vocab PDF", type="pdf")

# 3. Function to read the PDF
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# 4. Main App Logic
if api_key and uploaded_file:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Extract vocabulary from your PDF
    vocab_context = get_pdf_text(uploaded_file)
    
    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Say something in Japanese (or English)..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # The System Instructions (The "SOP")
        system_instruction = f"""
        You are a patient Japanese N5 teacher. 
        REFERENCE VOCABULARY: {vocab_context}
        
        RULES:
        1. Only use vocabulary from the provided list.
        2. Use simple ~desu/~masu forms.
        3. Provide: [Japanese with Kanji] -> [Furigana/Hiragana] -> [English Translation].
        4. If the user makes a mistake, correct them briefly in English.
        """

        # Generate Response
        full_prompt = f"{system_instruction}\n\nUser says: {prompt}"
        response = model.generate_content(full_prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
else:
    st.info("Please enter your API Key and upload your N5 PDF in the sidebar to start.")
