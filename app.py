import streamlit as st
import io
import hashlib
import re
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# ------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------

st.set_page_config(page_title="Treinamento EMP", layout="wide")

# ------------------------------
# CSS - FONTE 11
# ------------------------------

st.markdown("""
<style>
div[data-testid="stTextArea"] textarea {
    font-size: 11px !important;
}
</style>
""", unsafe_allow_html=True)

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

client = get_client()

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
# CLASSIFICADOR DE PERGUNTA
# ------------------------------

def tipo_pergunta(texto):
    if not texto:
        return "geral"

    t = texto.lower()

    if any(p in t for p in ["trajetoria", "trajetória", "sobre você", "quem é você"]):
        return "trajetoria"

    if any(p in t for p in ["desafio", "erro", "case", "problema", "situação", "conflito"]):
        return "star"

    if any(p in t for p in ["sql", "dados", "processo", "como fazer"]):
        return "tecnica"

    return "geral"

# ------------------------------
# TÍTULO
# ------------------------------

st.title("Treinamento EMP")

empresa = st.text_input("Empresa")

col1, col2 = st.columns(2)

with col1:
    vaga = st.text_area("Descrição da vaga", height=200)

with col2:
    uploaded_cv = st.file_uploader("Currículo", type=["pdf","docx","txt"])

    if uploaded_cv:
        st.session_state.cv_text = extrair_texto_cv(uploaded_cv)
        st.success("Currículo carregado")

# ------------------------------
# PERGUNTA
# ------------------------------

st.subheader("Pergunta da entrevista")

pergunta_digitada = st.text_input("Digite a pergunta ou use o microfone")
audio = audio_recorder(text="Click to record")

if pergunta_digitada:
    st.session_state.transcricao = pergunta_digitada

elif audio:
    audio_file = io.BytesIO(audio)
    audio_file.name = "audio.wav"

    transcricao = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )

    st.session_state.transcricao = transcricao.text

st.text_area("Pergunta detectada", value=st.session_state.transcricao, height=100)

# ------------------------------
# GERAR RESPOSTA
# ------------------------------

if st.session_state.transcricao:

    tipo = tipo_pergunta(st.session_state.transcricao)

    prompt_extra = ""

    # TRAJETÓRIA
    if tipo == "trajetoria":
        prompt_extra = """
Responder como narrativa profissional:
- início da carreira
- evolução
- experiências relevantes
- momento atual
- conexão com a vaga
Sem STAR.
"""

    # STAR
    elif tipo == "star":
        prompt_extra = """
Responder obrigatoriamente no formato:

S (Situação):
T (Tarefa):
A (Ação):
R (Resultado):

Curto, objetivo, 1 a 2 linhas por bloco.
"""

    # TÉCNICO
    elif tipo == "tecnica":
        prompt_extra = """
Resposta direta:
- lógica simples
- passos curtos
- código se necessário
"""

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
Responda como um humano em entrevista.

Seja claro, direto e natural.

{prompt_extra}
"""
            },
            {
                "role": "user",
                "content": f"""
Empresa: {empresa}
Vaga: {vaga}
Currículo: {st.session_state.cv_text}
Pergunta: {st.session_state.transcricao}
"""
            }
        ],
        max_tokens=220
    )

    st.session_state.resposta = resposta.choices[0].message.content

# ------------------------------
# RESPOSTA
# ------------------------------

st.subheader("Resposta estratégica")

st.text_area(
    "Resposta baseada na vaga, currículo e pergunta",
    value=st.session_state.resposta,
    height=220
)

# ------------------------------
# NOVO BLOCO - FERRAMENTAS
# ------------------------------

if st.session_state.resposta:

    st.subheader("Ferramentas utilizadas na resposta")

    with st.spinner("Identificando ferramentas..."):

        ferramentas_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Analise a resposta e identifique ferramentas utilizadas.

Regras:
- Listar até 5 ferramentas
- Explicar para que serviram
- Não inventar

Formato:
Ferramenta - uso
"""
                },
                {
                    "role": "user",
                    "content": st.session_state.resposta
                }
            ],
            max_tokens=150
        )

        st.info(ferramentas_resp.choices[0].message.content)
