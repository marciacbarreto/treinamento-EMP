import sounddevice as sd
import numpy as np
import queue
import time
import threading
import whisper
from openai import OpenAI

# =========================
# CONFIGURAÇÕES
# =========================
SAMPLE_RATE = 16000
CHUNK_DURATION = 2  # segundos por fragmento
MIN_WORDS_TO_ANSWER = 8
PAUSE_THRESHOLD = 1.5  # segundos de silêncio para considerar pergunta "completa"

# =========================
# FILAS E ESTADO
# =========================
audio_queue = queue.Queue()
text_queue = queue.Queue()

class QuestionBuffer:
    def __init__(self):
        self.text = ""
        self.last_update = time.time()

    def update(self, fragment):
        self.text += " " + fragment
        self.last_update = time.time()

    def is_ready(self):
        words = len(self.text.split())
        time_since_last = time.time() - self.last_update
        return words >= MIN_WORDS_TO_ANSWER and time_since_last > PAUSE_THRESHOLD

    def reset(self):
        self.text = ""

buffer = QuestionBuffer()

# =========================
# CONTEXTO (PERSONALIZE)
# =========================
context = {
    "cv": """
    Experiência em gestão de processos, indicadores, liderança de equipe,
    melhoria contínua, análise de dados e dashboards.
    """,
    "job": """
    Vaga exige liderança, análise de performance, melhoria operacional,
    tomada de decisão baseada em dados e comunicação com diretoria.
    """
}

# =========================
# MODELOS
# =========================
whisper_model = whisper.load_model("base")
client = OpenAI(api_key="SUA_API_KEY_AQUI")

# =========================
# CAPTURA DE ÁUDIO
# =========================
def audio_callback(indata, frames, time_info, status):
    audio_queue.put(indata.copy())

def start_audio_stream():
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback
    )
    stream.start()
    print("🎤 Capturando áudio...")
    return stream

# =========================
# TRANSCRIÇÃO
# =========================
def transcribe_worker():
    while True:
        if not audio_queue.empty():
            chunk = audio_queue.get()

            # Converter para formato whisper
            audio_np = np.squeeze(chunk)

            try:
                result = whisper_model.transcribe(audio_np, fp16=False)
                text = result["text"].strip()

                if text:
                    text_queue.put(text)
                    print(f"📝 Fragmento: {text}")

            except Exception as e:
                print("Erro na transcrição:", e)

# =========================
# DETECÇÃO DE PERGUNTA
# =========================
def is_question(text):
    triggers = [
        "tell me", "how", "why", "what", "describe",
        "can you", "do you", "have you", "?"
    ]
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in triggers)

# =========================
# CLASSIFICAÇÃO
# =========================
def classify_question(text):
    text_lower = text.lower()

    if "tell me about a time" in text_lower:
        return "behavioral"
    elif "how would you" in text_lower:
        return "situational"
    elif "improve" in text_lower or "process" in text_lower:
        return "process"
    elif "team" in text_lower or "leader" in text_lower:
        return "leadership"
    else:
        return "general"

# =========================
# PROMPT
# =========================
def build_prompt(question, context, q_type):
    return f"""
You are a professional job candidate in a live interview.

Question:
{question}

Question Type:
{q_type}

Candidate Background:
{context['cv']}

Job Requirements:
{context['job']}

Instructions:
- Answer naturally as spoken language
- Be concise (3 to 5 sentences)
- Be confident and professional
- Use real or plausible examples
- Include results or impact if possible
- Do NOT explain reasoning
- Do NOT use bullet points

Answer:
"""

# =========================
# LLM
# =========================
def generate_answer(prompt):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# =========================
# PROCESSAMENTO PRINCIPAL
# =========================
def processing_loop():
    while True:
        if not text_queue.empty():
            fragment = text_queue.get()

            buffer.update(fragment)
            current_text = buffer.text

            print(f"🧠 Buffer atual: {current_text}")

            if is_question(current_text):
                q_type = classify_question(current_text)

                if buffer.is_ready():
                    print("✅ Pergunta considerada completa")

                    prompt = build_prompt(current_text, context, q_type)
                    answer = generate_answer(prompt)

                    print("\n💬 RESPOSTA:")
                    print(answer)
                    print("-" * 50)

                    buffer.reset()

# =========================
# MAIN
# =========================
def main():
    start_audio_stream()

    threading.Thread(target=transcribe_worker, daemon=True).start()
    threading.Thread(target=processing_loop, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
