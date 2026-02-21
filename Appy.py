def play_audio(client, text, slow=True):
    """Robust 2026 TTS handler: searches all response parts for audio."""
    try:
        # Pacing instructions are now part of the text for 2.5 models
        pace = "[speed: 0.7]" if slow else "[speed: 1.0]"
        full_prompt = f"{pace} {text}"
        
        audio_res = client.models.generate_content(
            model='gemini-2.5-flash-tts',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                # Lowering temperature ensures the TTS engine stays focused on speech
                temperature=0.1 
            )
        )
        
        # New 2026 Logic: Iterate through all candidates and parts
        found_audio = False
        if audio_res.candidates:
            for part in audio_res.candidates[0].content.parts:
                if part.inline_data:
                    st.audio(part.inline_data.data, format="audio/wav", autoplay=True)
                    found_audio = True
                    break
        
        if not found_audio:
            st.warning("Sensei's voice is resting (No audio data returned).")
            
    except Exception as e:
        # Specifically catch 429 to tell you if you're clicking too fast
        if "429" in str(e):
            st.error("Slow down! Sensei can only speak a few times per minute on the free plan.")
        else:
            st.error(f"Voice Error: {str(e)}")

# --- In your Feedback Logic Section ---
if student_audio:
    with st.spinner("Sensei is listening..."):
        try:
            feedback_res = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    f"Context: {st.session_state.current_question}. Correct the student's Japanese. Be encouraging.",
                    types.Part.from_bytes(data=student_audio.read(), mime_type="audio/wav")
                ]
            )
            feedback_text = feedback_res.text
            st.success("Sensei's Feedback:")
            st.write(feedback_text)
            
            # Extract just the first sentence of feedback for the voice
            import re
            # Regex to grab the first Japanese or English sentence
            first_sentence = re.split(r'[.!?।।！？]', feedback_text)[0]
            play_audio(client, first_sentence, slow=False)
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
