import streamlit as st
from audio_recorder_streamlit import audio_recorder

st.set_page_config(layout="wide")

st.title("Treinamento EMP")
st.caption("Análise da vaga + currículo e simulação de entrevista")

# EMPRESA
empresa = st.text_input("Empresa")

# VAGA + CURRÍCULO
col1, col2 = st.columns(2)

with col1:
    vaga = st.text_area("Descrição da Vaga", height=200)

with col2:
    cv = st.file_uploader("Currículo", type=["pdf","docx","txt"])

# FERRAMENTAS
st.subheader("Ferramentas que a empresa trabalha (Explicação)")

st.info("""
Jira (gestão de backlog e tarefas ágeis) /
Confluence (documentação e governança de processos) /
Miro (mapas colaborativos e desenho de jornadas) /
Google Analytics (análise de comportamento no e-commerce) /
Power BI (monitoramento de indicadores e dashboards) /
Adobe Experience Manager (gestão de conteúdo digital) /
Slack (comunicação entre áreas) /
ChatGPT (IA para análise e otimização de processos)
""")

# BOTÕES
colb1, colb2, colb3 = st.columns(3)

with colb1:
    iniciar = st.button("Iniciar")

with colb2:
    atualizar = st.button("Atualizar")

with colb3:
    encerrar = st.button("Encerrar")

st.divider()

# MICROFONE
st.subheader("🎤 Microfone / Áudio")

audio = audio_recorder()

# RESPOSTA
st.subheader("Resposta Estratégica")

resposta = st.text_area(
"Resposta de acordo com a vaga, currículo e pergunta",
height=250
)
