import io
import streamlit as st
import requests
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

# ================= CONFIG =================
st.set_page_config(page_title="Treinamento EMP", layout="centered")
st.title("Treinamento EMP")

# ================= STATE =================
def init_state():
    defaults = {
        "logged": False,
        "running": False,
        "analise_estrategica": "",
        "curriculo": "",
        "vaga": "",
        "empresa": "",
        "campo_transcricao": "",
        "campo_resposta": "",
        "last_audio_len": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ================= OPENAI =================
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY não encontrada.")
        st.stop()
    return OpenAI(api_key=api_key)

# ================= LEITOR ARQUIVOS =================
def extract_text(uploaded_file):
    if not uploaded_file:
        return ""
    data = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join(p.extract_text() or "" for p in reader.pages)

    if name.endswith(".docx"):
        import docx
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    return data.decode("utf-8", errors="ignore")

# ================= ANALISE ESTRATÉGICA =================
def gerar_analise(curriculo, vaga, empresa):
    client = get_openai_client()

    prompt = f"""
    Analise estrategicamente o alinhamento entre currículo e vaga.

    EMPRESA: {empresa}

    VAGA:
    {vaga}

    CURRÍCULO:
    {curriculo}

    Gere:
    - Pontos fortes aderentes
    - Lacunas
    - Competências-chave
    - Estratégia de posicionamento
    """

    resp = client.responses.create(
        model="gpt-5.2",
        input=prompt
    )

    return resp.output_text.strip()

# ================= RESPOSTA ENTREVISTA =================
def gerar_resposta(curriculo, vaga, empresa, pergunta):
    client = get_openai_client()

    prompt = f"""
    Você é um treinador de entrevista.

    EMPRESA: {empresa}
    VAGA: {vaga}
    CURRÍCULO: {curriculo}
    PERGUNTA: {pergunta}

    Gere resposta profissional, estratégica,
    até 8 linhas (10 se for case).
    Não invente informações.
    """

    resp = client.responses.create(
        model="gpt-5.2",
        input=prompt
    )

    return resp.output_text.strip()

# ================= LOGIN =================
if not st.session_state.logged:
    st.subheader("Login")
    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user and password:
            st.session_state.logged = True
            st.rerun()
        else:
            st.warning("Preencha usuário e senha.")

    st.stop()

# ================= BLOCO ESTRATÉGICO =================
st.header("Dados Estratégicos")

empresa = st.text_input("Empresa", value=st.session_state.empresa)
vaga_text = st.text_area("Descrição da Vaga", value=st.session_state.vaga)
curr_file = st.file_uploader("Upload do Currículo", type=["pdf", "docx", "txt"])

if st.button("Atualizar Análise"):
    st.session_state.empresa = empresa.strip()
    st.session_state.vaga = vaga_text.strip()
    st.session_state.curriculo = extract_text(curr_file)

    if st.session_state.empresa and st.session_state.vaga and st.session_state.curriculo:
        with st.spinner("Gerando análise estratégica..."):
            st.session_state.analise_estrategica = gerar_analise(
                st.session_state.curriculo,
                st.session_state.vaga,
                st.session_state.empresa
            )
    else:
        st.warning("Preencha todos os campos antes de gerar análise.")

st.subheader("Análise Estratégica")
st.text_area(
    "",
    value=st.session_state.analise_estrategica,
    height=200,
    disabled=True
)

# ================= BLOCO ENTREVISTA =================
st.header("Simulação de Entrevista")

col1, col2 = st.columns(2)

with col1:
    iniciar = st.button("Iniciar")

with col2:
    if st.button("Encerrar"):
        for k in st.session_state.keys():
            st.session_state[k] = ""
        st.session_state.logged = True
        st.rerun()

# Só permite iniciar se houver análise
if iniciar:
    if not st.session_state.analise_estrategica:
        st.warning("Gere a análise estratégica antes de iniciar.")
    else:
        st.session_state.running = True

if st.session_state.running:

    audio_bytes = audio_recorder(text="Falar agora")

    if audio_bytes and len(audio_bytes) != st.session_state.last_audio_len:
        st.session_state.last_audio_len = len(audio_bytes)

        client = get_openai_client()

        with st.spinner("Transcrevendo..."):
            tr = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=io.BytesIO(audio_bytes)
            )
            pergunta = tr.text.strip()

        st.session_state.campo_transcricao = pergunta

        with st.spinner("Gerando resposta..."):
            resposta = gerar_resposta(
                st.session_state.curriculo,
                st.session_state.vaga,
                st.session_state.empresa,
                pergunta
            )

        st.session_state.campo_resposta = resposta
        st.rerun()

st.subheader("Transcrição da Pergunta")
st.text_area("", value=st.session_state.campo_transcricao, height=120, disabled=True)

st.subheader("Resposta Estratégica")
st.text_area("", key="campo_resposta", height=180)
