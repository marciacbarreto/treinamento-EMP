import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# CONFIGURAÇÃO
st.set_page_config(page_title="Treinamento EMP", layout="wide")

defaults = {
    "logged": False,
    "analise_gerada": False,
    "modo_entrevista": False,
    "empresa": "",
    "vaga": "",
    "analise_estrategica": "",
    "transcricao": "",
    "resposta_ideal": "",
    "last_audio_hash": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# CLIENTE OPENAI
def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    return OpenAI(api_key=api_key)


# EXTRAÇÃO DE TEXTO DO CURRÍCULO
def extrair_texto_cv(uploaded_file):

    if uploaded_file is None:
        return ""

    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        pdf = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([p.extract_text() for p in pdf.pages])

    elif name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")


# LOGIN
if not st.session_state.logged:

    st.title("🔐 Login - Treinamento EMP")

    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user and password:
            st.session_state.logged = True
            st.rerun()

    st.stop()


# SISTEMA
st.title("🎯 Treinamento EMP")

st.caption(
"Plataforma para análise de vagas e simulação de entrevistas com resposta estratégica baseada na vaga e no currículo."
)

# BLOCO 1
st.header("🔷 BLOCO 1 — DADOS ESTRATÉGICOS")

col1, col2 = st.columns(2)

with col1:

    empresa = st.text_input("Empresa", value=st.session_state.empresa)

    vaga = st.text_area(
        "Descrição da vaga",
        value=st.session_state.vaga,
        height=180
    )

    uploaded_cv = st.file_uploader(
        "Upload do Currículo",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_cv:
        st.success("Currículo carregado com sucesso")

    if st.button("Atualizar Análise"):

        if empresa and vaga and uploaded_cv:

            with st.spinner("Analisando vaga e currículo..."):

                cv_text = extrair_texto_cv(uploaded_cv)

                st.session_state.empresa = empresa
                st.session_state.vaga = vaga

                client = get_client()

                resposta = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[

                        {
                            "role": "system",
                            "content": """
Analise a vaga e o currículo.

Retorne apenas:

1) Breve análise do que a empresa busca
2) Estratégia de resposta para entrevista

A estratégia deve destacar:

- gestão de projetos e governança
- análise de dados e indicadores
- melhoria contínua de processos
- uso de tecnologia e inteligência artificial
- capacidade de conectar áreas e garantir alinhamento estratégico
"""
                        },

                        {
                            "role": "user",
                            "content": f"""
Empresa: {empresa}

Descrição da vaga:
{vaga}

Currículo:
{cv_text}
"""
                        }
                    ]
                )

                st.session_state.analise_estrategica = resposta.choices[0].message.content
                st.session_state.analise_gerada = True
                st.rerun()


with col2:

    st.subheader("Análise Estratégica")

    st.info(
        st.session_state.analise_estrategica
        or "Aguardando análise da vaga e currículo."
    )


st.divider()

# BLOCO 2
st.header("🔷 BLOCO 2 — SIMULAÇÃO DE ENTREVISTA")

if st.session_state.analise_gerada:

    colA, colB = st.columns([1, 5])

    with colA:

        if st.button("▶️ Iniciar"):
            st.session_state.modo_entrevista = True

    with colB:

        if st.button("🛑 Encerrar"):

            for key in [
                "analise_gerada",
                "modo_entrevista",
                "analise_estrategica",
                "transcricao",
                "resposta_ideal"
            ]:
                st.session_state[key] = ""

            st.rerun()


    if st.session_state.modo_entrevista:

        st.write("🎤 Escutar pergunta da entrevista")

        audio = audio_recorder(
            text="",
            neutral_color="#2ecc71"
        )

        if audio:

            audio_hash = hashlib.sha1(audio).hexdigest()

            if audio_hash != st.session_state.last_audio_hash:

                st.session_state.last_audio_hash = audio_hash

                client = get_client()

                with st.spinner("Gerando resposta estratégica..."):

                    audio_file = io.BytesIO(audio)
                    audio_file.name = "audio.wav"

                    tr = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )

                    st.session_state.transcricao = tr.text

                    resposta = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[

                            {
                                "role": "system",
                                "content": f"""
Use esta estratégia de resposta:

{st.session_state.analise_estrategica}

Responda como um candidato ideal.

A resposta deve destacar naturalmente:

- gestão de projetos e governança
- análise de dados e indicadores
- melhoria contínua de processos
- uso de tecnologia e inteligência artificial
- conexão entre áreas e alinhamento estratégico
"""
                            },

                            {
                                "role": "user",
                                "content": f"""
Empresa: {st.session_state.empresa}

Pergunta do recrutador:
{tr.text}
"""
                            }
                        ]
                    )

                    st.session_state.resposta_ideal = resposta.choices[0].message.content
                    st.rerun()


        st.text_input(
            "Pergunta detectada",
            value=st.session_state.transcricao,
            disabled=True
        )


        nova_resp = st.text_area(
            "Resposta estratégica (gerada automaticamente)",
            value=st.session_state.resposta_ideal,
            height=220
        )


        if st.button("🔄 Refinar Resposta"):

            st.session_state.resposta_ideal = nova_resp
            st.success("Resposta atualizada")


        st.caption(
        "Resposta gerada com base na descrição da vaga e no currículo."
        )


st.divider()

# RODAPÉ

st.caption("""
Ferramentas utilizadas:

Jira (gestão de backlog e tarefas ágeis) /
Confluence (documentação e governança) /
Miro (mapas colaborativos e jornadas) /
Google Analytics (comportamento do usuário no e-commerce) /
Power BI (monitoramento de indicadores e dashboards) /
Adobe Experience Manager (gestão de conteúdo digital) /
Slack (comunicação entre áreas) /
ChatGPT (IA para análise e otimização de processos)
""")
