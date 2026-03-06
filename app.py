# -------------------------
# PERGUNTA DA ENTREVISTA
# -------------------------

st.subheader("Pergunta da entrevista")

# campo para digitar pergunta
pergunta_digitada = st.text_input(
    "Digite a pergunta ou use o microfone"
)

# microfone
audio = audio_recorder(text="Click to record")

client = get_client()

# -------------------------
# SE PERGUNTA FOR DIGITADA
# -------------------------

if pergunta_digitada:

    st.session_state.transcricao = pergunta_digitada

# -------------------------
# SE PERGUNTA VIER DO ÁUDIO
# -------------------------

elif audio:

    audio_hash = hashlib.sha1(audio).hexdigest()

    if audio_hash != st.session_state.last_audio_hash:

        st.session_state.last_audio_hash = audio_hash

        with st.spinner("Transcrevendo pergunta..."):

            audio_file = io.BytesIO(audio)
            audio_file.name = "audio.wav"

            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            st.session_state.transcricao = transcricao.text
