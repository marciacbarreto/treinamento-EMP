import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# ------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------

st.set_page_config(page_title="Treinamento EMP", layout="wide")

# ------------------------------
# ESTADO DA SESSÃO
# ------------------------------

defaults = {
    "transcricao": "",
    "resposta": "",
    "cv_text": "",
    "last_audio_hash": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ------------------------------
# CLIENTE OPENAI
# ------------------------------

def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)

# ------------------------------
# EXTRAIR TEXTO DO CURRÍCULO
# ------------------------------

def extrair_texto_cv(uploaded_file):

    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        pdf = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

    elif name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

# ------------------------------
# TÍTULO
# ------------------------------

st.title("Treinamento EMP")

# ------------------------------
# EMPRESA
# ------------------------------

empresa = st.text_input("Empresa")

# ------------------------------
# DESCRIÇÃO DA VAGA + CURRÍCULO
# ------------------------------

col1, col2 = st.columns(2)

with col1:

    vaga = st.text_area(
        "Descrição da vaga",
        height=200
    )

with col2:

    uploaded_cv = st.file_uploader(
        "Currículo",
        type=["pdf","docx","txt"]
    )

    if uploaded_cv:
        st.session_state.cv_text = extrair_texto_cv(uploaded_cv)
        st.success("Currículo carregado")

# ------------------------------
# FERRAMENTAS DA EMPRESA
# ------------------------------

st.subheader("Ferramentas que a empresa trabalha (Explicação)")

if empresa and vaga:

    with st.spinner("Identificando ferramentas utilizadas pela empresa..."):

        client = get_client()

        resposta_tools = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Identifique as principais ferramentas utilizadas pela empresa
com base na descrição da vaga.

Liste até 6 ferramentas utilizadas nessa área.

Formato obrigatório:
Ferramenta (explicação curta) / Ferramenta (explicação curta)

As ferramentas devem estar relacionadas a:
operações, CRM, análise de dados, automação e gestão de processos.
"""
                },
                {
                    "role": "user",
                    "content": f"""
Empresa: {empresa}

Descrição da vaga:
{vaga}

Currículo:
{st.session_state.cv_text}
"""
                }
            ],
            max_tokens=120
        )

        ferramentas = resposta_tools.choices[0].message.content

        st.info(ferramentas)

# ------------------------------
# BOTÕES
# ------------------------------

colb1, colb2, colb3 = st.columns(3)

with colb1:
    iniciar = st.button("Iniciar")

with colb2:
    atualizar = st.button("Atualizar")

with colb3:
    encerrar = st.button("Encerrar")

st.divider()

# ------------------------------
# PERGUNTA DA ENTREVISTA
# ------------------------------

st.subheader("Pergunta da entrevista")

pergunta_digitada = st.text_input(
    "Digite a pergunta ou use o microfone"
)

audio = audio_recorder(text="Click to record")

client = get_client()

# ------------------------------
# PERGUNTA DIGITADA
# ------------------------------

if pergunta_digitada:

    st.session_state.transcricao = pergunta_digitada

# ------------------------------
# PERGUNTA POR ÁUDIO
# ------------------------------

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

# ------------------------------
# TRANSCRIÇÃO
# ------------------------------

st.subheader("Transcrição da pergunta")

st.text_area(
    "Pergunta detectada",
    value=st.session_state.transcricao,
    height=100
)

# ------------------------------
# GERAR RESPOSTA
# ------------------------------

if st.session_state.transcricao:

    with st.spinner("Gerando resposta estratégica..."):

        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Responda como um humano em entrevista, de forma natural e direta.

Regras:
- Seja rápido e objetivo
- Não invente informação
- Não repita conteúdo
- Use tom coloquial, como conversa
- Só aprofunde se a pergunta exigir
- Se a pergunta for simples, responda em 1 ou 2 frases
- Evite linguagem robótica ou técnica excessiva
"""
                },
                {
                    "role": "user",
                    "content": f"""
Empresa: {empresa}

Descrição da vaga:
{vaga}

Currículo:
{st.session_state.cv_text}

Pergunta:
{st.session_state.transcricao}
"""
                }
            ],
            max_tokens=120
        )

        st.session_state.resposta = resposta.choices[0].message.content

# ------------------------------
# RESPOSTA
# ------------------------------

st.subheader("Resposta estratégica")

st.text_area(
    "Resposta baseada na vaga, currículo e pergunta",
    value=st.session_state.resposta,
    height=180
)
