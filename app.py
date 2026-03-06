import streamlit as st
import io
import hashlib
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder
import PyPDF2
import docx

# --- 1. CONFIGURAÇÃO E REGRAS ---
st.set_page_config(page_title="Treinamento EMP", layout="wide", initial_sidebar_state="collapsed")

RODAPE_FERRAMENTAS = (
    "Jira (backlog e tarefas ágeis) / Confluence (documentação e governança) / "
    "Miro (mapas e jornadas) / Google Analytics (comportamento no e-commerce) / "
    "Power BI (KPIs e dashboards) / Adobe Experience Manager (conteúdo digital) / "
    "Slack (colaboração entre áreas) / ChatGPT (IA para análise e otimização)"
)

PALAVRAS_CHAVE = [
    "gestão de projetos e estruturação de governança",
    "análise de dados e monitoramento de indicadores",
    "melhoria contínua de processos",
    "uso de tecnologia e inteligência artificial para otimização",
    "capacidade de conectar áreas e garantir alinhamento estratégico"
]

# --- 2. MEMÓRIA DO SISTEMA ---
if "logged" not in st.session_state: st.session_state.logged = False
if "analise_gerada" not in st.session_state: st.session_state.analise_gerada = False
if "modo_entrevista" not in st.session_state: st.session_state.modo_entrevista = False
if "analise_estrategica" not in st.session_state: st.session_state.analise_estrategica = ""
if "resposta_ideal" not in st.session_state: st.session_state.resposta_ideal = ""
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = ""

def get_client():
    return OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def extrair_texto_cv(uploaded_file):
    if not uploaded_file: return ""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        pdf = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    elif name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    return uploaded_file.read().decode("utf-8", errors="ignore")

# --- 3. LOGIN ---
if not st.session_state.logged:
    st.title("🔐 Login - Treinamento EMP")
    u, p = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar") and u and p:
        st.session_state.logged = True
        st.rerun()
    st.stop()

# --- 4. SISTEMA ---
st.title("🎯 Treinamento EMP")

# BLOCO 1: DADOS ESTRATÉGICOS
st.header("🔷 BLOCO 1 — DADOS ESTRATÉGICOS")
c1, c2 = st.columns(2)

with c1:
    emp = st.text_input("Empresa", key="emp_input")
    desc = st.text_area("Descrição da Vaga", height=150, key="vaga_input")
    uploaded_cv = st.file_uploader("Upload do Currículo", type=["pdf", "docx", "txt"])

    if st.button("Atualizar Análise"):
        if emp and desc and uploaded_cv:
            with st.spinner("Cruzando Vaga, CV e Empresa..."):
                cv_text = extrair_texto_cv(uploaded_cv)
                client = get_client()
                prompt_b1 = f"Analise o CV para a vaga na {emp}. Foque em: {', '.join(PALAVRAS_CHAVE)}."
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": prompt_b1},
                              {"role": "user", "content": f"Vaga: {desc}\nCV: {cv_text}"}]
                )
                st.session_state.analise_estrategica = res.choices[0].message.content
                st.session_state.cv_text = cv_text
                st.session_state.empresa = emp
                st.session_state.analise_gerada = True
                st.rerun()

with c2:
    st.subheader("Análise Estratégica")
    st.info(st.session_state.analise_estrategica or "Aguardando atualização...")

st.divider()

# BLOCO 2: SIMULAÇÃO COM RESPOSTA AUTOMÁTICA
st.header("🔷 BLOCO 2 — SIMULAÇÃO DE ENTREVISTA")

if st.session_state.analise_gerada:
    if st.button("▶️ Iniciar Simulação"): st.session_state.modo_entrevista = True
    
    if st.session_state.modo_entrevista:
        st.write("🎤 **Fale a pergunta agora:**")
        audio = audio_recorder(text="Escutar pergunta da entrevista", neutral_color="#2ecc71")
        
        if audio:
            a_hash = hashlib.sha1(audio).hexdigest()
            if a_hash != st.session_state.last_audio_hash:
                st.session_state.last_audio_hash = a_hash
                client = get_client()
                with st.spinner("Gerando Resposta Estratégica Automática..."):
                    # Transcrição silenciosa (apenas para processamento)
                    tr = client.audio.transcriptions.create(model="whisper-1", file=("a.wav", io.BytesIO(audio)))
                    
                    # Resposta estratégica com cruzamento obrigatório
                    prompt_b2 = f"""
                    Você é um candidato sendo entrevistado na empresa {st.session_state.empresa}.
                    Estratégia base: {st.session_state.analise_estrategica}
                    Evidências do CV: {st.session_state.cv_text[:2000]}
                    
                    REGRAS:
                    - Responda DIRETAMENTE à pergunta ouvida.
                    - Tom convincente, objetivo e de conversa.
                    - Inclua OBRIGATORIAMENTE: {', '.join(PALAVRAS_CHAVE)}.
                    - Termine com este rodapé exatamente: {RODAPE_FERRAMENTAS}
                    """
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": prompt_b2},
                                  {"role": "user", "content": f"Pergunta ouvida: {tr.text}"}]
                    )
                    st.session_state.resposta_ideal = resp.choices[0].message.content
                    st.rerun()

        # SAÍDA DIRETA: Mostra apenas a Resposta Sugerida
        if st.session_state.resposta_ideal:
            st.subheader("Sugestão de Resposta Estratégica")
            st.write(st.session_state.resposta_ideal)
