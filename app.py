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
# CLASSIFICADOR
# ------------------------------

def tipo_pergunta(texto):
    t = texto.lower()

    if "trajet" in t:
        return "trajetoria"

    if any(p in t for p in ["desafio", "case", "erro", "problema"]):
        return "star"

    return "geral"

# ------------------------------
# UI
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

# ------------------------------
# PERGUNTA
# ------------------------------

pergunta = st.text_input("Pergunta")

if pergunta:
    st.session_state.transcricao = pergunta

# ------------------------------
# RESPOSTA
# ------------------------------

if st.session_state.transcricao:

    tipo = tipo_pergunta(st.session_state.transcricao)

    prompt_contexto = f"""
Responda considerando a empresa e a vaga.

Se a vaga indicar uso de CRM ou atendimento:
- Utilize como base Salesforce e Zendesk
- Mas adapte conforme o contexto da empresa

Use esta base obrigatória na resposta:

"Eu costumo trabalhar com relatórios extraídos de ferramentas como Salesforce e Zendesk para entender tanto a performance comercial quanto operacional. 
No Salesforce, analiso produtividade, carteira e volume; no Zendesk, acompanho SLA, backlog e motivos de contato. 
Como coordenadora, meu papel é analisar esses dados, direcionar o time e garantir que as ferramentas estejam bem estruturadas para gerar insights. 
A partir disso, consolido as informações em dashboards, como no Power BI, e consigo identificar gargalos, direcionar melhorias e apoiar a tomada de decisão."

A resposta deve:
- ser natural
- adaptar levemente ao contexto da vaga
- não parecer decorada
- manter clareza e objetividade
"""

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_contexto},
            {"role": "user", "content": f"""
Empresa: {empresa}
Vaga: {vaga}
Pergunta: {st.session_state.transcricao}
"""}
        ],
        max_tokens=200
    )

    st.session_state.resposta = resposta.choices[0].message.content

# ------------------------------
# EXIBIÇÃO
# ------------------------------

st.subheader("Resposta estratégica")

st.text_area(
    "Resposta",
    value=st.session_state.resposta,
    height=220
)

# ------------------------------
# FERRAMENTAS (ADICIONADO)
# ------------------------------

if st.session_state.resposta:

    st.subheader("Ferramentas utilizadas na resposta")

    ferramentas = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
Liste as ferramentas citadas na resposta e explique para que servem.

Formato:
Ferramenta - uso
"""
            },
            {
                "role": "user",
                "content": st.session_state.resposta
            }
        ],
        max_tokens=120
    )

    st.info(ferramentas.choices[0].message.content)
