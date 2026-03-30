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
# CSS - FONTE 12
# ------------------------------

st.markdown("""
<style>
div[data-testid="stTextArea"] textarea {
    font-size: 12px !important;
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
    "last_audio_hash": "",
    "ferramentas_resposta": ""
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
# CLASSIFICAÇÃO DA PERGUNTA
# ------------------------------

def tipo_pergunta(texto: str) -> str:
    if not texto:
        return "geral"

    t = texto.lower().strip()

    if any(p in t for p in [
        "trajetoria", "trajetória", "fale sobre você", "conte sobre você",
        "apresente-se", "me fale da sua carreira", "conte sua carreira"
    ]):
        return "trajetoria"

    if any(p in t for p in [
        "conte um case", "me conte um case", "fale de um case",
        "conte uma situação", "me fale de uma situação",
        "desafio", "problema", "erro", "conflito", "resultado",
        "exemplo", "case da gol", "conte um exemplo", "me dê um exemplo",
        "situação", "quando você", "ocasião em que"
    ]):
        return "star"

    if any(p in t for p in [
        "sql", "power bi", "dashboard", "dados", "query", "processo",
        "como fazer", "como funciona", "fluxo", "arquitetura", "indicador",
        "kpi", "causa raiz"
    ]):
        return "tecnica"

    return "geral"

# ------------------------------
# VALIDAÇÃO STAR
# ------------------------------

def validar_star(texto: str) -> bool:
    if not texto:
        return False

    padroes = [
        r"(?im)^\s*S\s*\(\s*Situa[cç][aã]o\s*\)\s*:",
        r"(?im)^\s*T\s*\(\s*Tarefa\s*\)\s*:",
        r"(?im)^\s*A\s*\(\s*A[cç][aã]o\s*\)\s*:",
        r"(?im)^\s*R\s*\(\s*Resultado\s*\)\s*:"
    ]

    return all(re.search(p, texto) for p in padroes)

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
    vaga = st.text_area("Descrição da vaga", height=200)

with col2:
    uploaded_cv = st.file_uploader("Currículo", type=["pdf", "docx", "txt"])

    if uploaded_cv:
        st.session_state.cv_text = extrair_texto_cv(uploaded_cv)
        st.success("Currículo carregado")

# ------------------------------
# BOTÕES DE CONTROLE
# ------------------------------

colb1, colb2, colb3 = st.columns(3)

with colb1:
    iniciar = st.button("Iniciar")

with colb2:
    atualizar = st.button("Atualizar")

with colb3:
    encerrar = st.button("Encerrar")

if "rodando" not in st.session_state:
    st.session_state.rodando = False

if iniciar:
    st.session_state.rodando = True

if encerrar:
    st.session_state.rodando = False
    st.session_state.transcricao = ""
    st.session_state.resposta = ""
    st.session_state.ferramentas_resposta = ""

if atualizar:
    st.experimental_rerun()

if not st.session_state.rodando:
    st.info("Clique em Iniciar para começar")
    st.stop()

# ------------------------------
# PERGUNTA DA ENTREVISTA
# ------------------------------

st.subheader("Pergunta da entrevista")

pergunta_digitada = st.text_input("Digite a pergunta ou use o microfone")
audio = audio_recorder(text="Click to record")

# ------------------------------
# PERGUNTA DIGITADA / ÁUDIO
# ------------------------------

if pergunta_digitada:
    st.session_state.transcricao = pergunta_digitada

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
    tipo = tipo_pergunta(st.session_state.transcricao)

    if tipo == "trajetoria":
        prompt_extra = """A pergunta é de trajetória..."""

    elif tipo == "star":
        prompt_extra = """A pergunta é comportamental/case..."""

    elif tipo == "tecnica":
        prompt_extra = """A pergunta é técnica..."""

    else:
        prompt_extra = """Responder de forma clara, curta, natural e conectada à vaga."""

    with st.spinner("Gerando resposta estratégica..."):
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
Responda como um humano em entrevista.

Regras gerais:
- Fale como uma pessoa real, não como texto perfeito
- Evite frases muito estruturadas ou ensaiadas
- Traga o problema de forma concreta
- Explique o que você fez e como fez
- Mostre decisão
- Conecte ação com impacto
- Não invente informação
- Use currículo e vaga
- Seja direto, mas não superficial

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
            max_tokens=260
        )

        st.session_state.resposta = resposta.choices[0].message.content.strip()

# ------------------------------
# RESPOSTA
# ------------------------------

st.subheader("Resposta estratégica")

st.text_area(
    "Resposta baseada na vaga, currículo e pergunta",
    value=st.session_state.resposta,
    height=240
)
