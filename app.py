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
# CSS - FONTE MENOR
# ------------------------------

st.markdown("""
<style>
div[data-testid="stTextArea"] textarea {
    font-size: 10px !important;
}
.star-box {
    border: 1px solid #d9d9d9;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 8px;
    background-color: #fafafa;
    font-size: 10px;
}
.star-ok {
    color: #1a7f37;
    font-weight: 600;
    font-size: 10px;
}
.star-miss {
    color: #b42318;
    font-weight: 600;
    font-size: 10px;
}
.small-label {
    font-size: 10px;
    font-weight: 600;
    margin-bottom: 4px;
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
# FUNÇÕES STAR
# ------------------------------

def is_pergunta_comportamental(texto: str) -> bool:
    if not texto:
        return False

    texto = texto.lower()
    gatilhos = [
        "conte", "me fale", "case", "situação", "desafio", "problema",
        "erro", "conflito", "resultado", "exemplo", "fraqueza",
        "ponto fraco", "liderança", "pressão", "black friday",
        "como você resolveu", "o que você fez"
    ]
    return any(g in texto for g in gatilhos)

def validar_star_explicito(texto: str) -> dict:
    if not texto:
        return {"S": False, "T": False, "A": False, "R": False}

    padroes = {
        "S": r"(?im)^\s*S\s*\(\s*Situa[cç][aã]o\s*\)\s*:",
        "T": r"(?im)^\s*T\s*\(\s*Tarefa\s*\)\s*:",
        "A": r"(?im)^\s*A\s*\(\s*A[cç][aã]o\s*\)\s*:",
        "R": r"(?im)^\s*R\s*\(\s*Resultado\s*\)\s*:"
    }

    return {k: bool(re.search(v, texto)) for k, v in padroes.items()}

def extrair_bloco_star(texto: str, letra: str, titulo: str) -> str:
    if not texto:
        return ""

    pattern = rf"(?is){letra}\s*\(\s*{titulo}\s*\)\s*:\s*(.*?)(?=\n\s*[STAR]\s*\(|\Z)"
    m = re.search(pattern, texto)
    if m:
        return m.group(1).strip()
    return ""

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
        type=["pdf", "docx", "txt"]
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
        pergunta_atual = st.session_state.transcricao
        pergunta_eh_star = is_pergunta_comportamental(pergunta_atual)

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
- Use tom coloquial
- Evite linguagem robótica

---

# STAR (OBRIGATÓRIO E VISÍVEL)

- Para qualquer pergunta comportamental, case, desafio, erro, conflito, fraqueza ou resultado, a resposta DEVE vir exatamente neste formato:

S (Situação):
- Contextualize rapidamente onde e quando aconteceu.

T (Tarefa):
- Explique qual era o problema ou desafio específico.

A (Ação):
- Descreva exatamente o que você fez.
- Foque no "eu", não apenas no "nós".

R (Resultado):
- Mostre o resultado com números, ganhos, redução de problema, melhoria ou aprendizado.

Regras do formato:
- Os blocos S, T, A e R devem aparecer escritos.
- Cada bloco deve ter 1 ou 2 linhas.
- A resposta inteira deve ser curta e objetiva.
- Não juntar tudo em um único parágrafo.
- Se a pergunta for comportamental e a resposta não vier em STAR, a resposta está incorreta.

---

# PADRÃO PARAKEET

- Se for técnico:
  - resposta direta
  - lógica simples
  - passos curtos
  - código apenas se necessário

---

# OBJETIVO FINAL

- Resposta clara, curta, natural e com impacto.
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
{pergunta_atual}
"""
                }
            ],
            max_tokens=220
        )

        resposta_texto = resposta.choices[0].message.content.strip()

        # Validação automática do STAR
        if pergunta_eh_star:
            validacao = validar_star_explicito(resposta_texto)

            if not all(validacao.values()):
                with st.spinner("Ajustando resposta para o formato STAR..."):
                    correcao = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": """
Reescreva a resposta obrigatoriamente no formato:

S (Situação):
...

T (Tarefa):
...

A (Ação):
...

R (Resultado):
...

Regras:
- Não remover o conteúdo principal.
- Deixar curto, objetivo e claro.
- Cada bloco com 1 ou 2 linhas.
- Não usar texto corrido.
- Não inventar informação.
"""
                            },
                            {
                                "role": "user",
                                "content": f"""
Pergunta:
{pergunta_atual}

Resposta atual:
{resposta_texto}
"""
                            }
                        ],
                        max_tokens=220
                    )

                    resposta_texto = correcao.choices[0].message.content.strip()

        st.session_state.resposta = resposta_texto

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
# VALIDAÇÃO STAR VISUAL
# ------------------------------

if st.session_state.resposta:
    st.subheader("Validação STAR")

    status_star = validar_star_explicito(st.session_state.resposta)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if status_star["S"]:
            st.markdown('<div class="star-ok">S encontrado</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="star-miss">S ausente</div>', unsafe_allow_html=True)

    with c2:
        if status_star["T"]:
            st.markdown('<div class="star-ok">T encontrado</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="star-miss">T ausente</div>', unsafe_allow_html=True)

    with c3:
        if status_star["A"]:
            st.markdown('<div class="star-ok">A encontrado</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="star-miss">A ausente</div>', unsafe_allow_html=True)

    with c4:
        if status_star["R"]:
            st.markdown('<div class="star-ok">R encontrado</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="star-miss">R ausente</div>', unsafe_allow_html=True)

    if all(status_star.values()):
        st.success("Resposta validada com STAR completo.")
    elif is_pergunta_comportamental(st.session_state.transcricao):
        st.warning("A resposta não ficou 100% no formato STAR.")
    else:
        st.info("Pergunta aparentemente não comportamental. STAR pode não ser necessário.")

# ------------------------------
# STAR VISUAL
# ------------------------------

if st.session_state.resposta:
    st.subheader("Estrutura STAR (visual)")

    s_txt = extrair_bloco_star(st.session_state.resposta, "S", "Situação")
    t_txt = extrair_bloco_star(st.session_state.resposta, "T", "Tarefa")
    a_txt = extrair_bloco_star(st.session_state.resposta, "A", "Ação")
    r_txt = extrair_bloco_star(st.session_state.resposta, "R", "Resultado")

    col_star_1, col_star_2 = st.columns(2)

    with col_star_1:
        st.markdown('<div class="small-label">S (Situação)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="star-box">{s_txt if s_txt else "Não identificado"}</div>', unsafe_allow_html=True)

        st.markdown('<div class="small-label">T (Tarefa)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="star-box">{t_txt if t_txt else "Não identificado"}</div>', unsafe_allow_html=True)

    with col_star_2:
        st.markdown('<div class="small-label">A (Ação)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="star-box">{a_txt if a_txt else "Não identificado"}</div>', unsafe_allow_html=True)

        st.markdown('<div class="small-label">R (Resultado)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="star-box">{r_txt if r_txt else "Não identificado"}</div>', unsafe_allow_html=True)
