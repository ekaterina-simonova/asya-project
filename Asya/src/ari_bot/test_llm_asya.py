import json
import sys
from pathlib import Path
from typing import List, Dict

from llama_cpp import Llama


# ---------- Пути к модели и промпту ----------

# Корень проекта Asya (…/Asya/)
BASE_DIR = Path(__file__).resolve().parents[2]

# Файл промпта Аси
PROMPT_PATH = BASE_DIR / "prompts" / "full_prompt.txt"

# Путь к модели GGUF ()
MODEL_PATH = Path("/home/tulauser/models/Mistral-NeMo-Minitron-8B-Instruct-Q6_K.gguf")


# ---------- Вспомогательные функции ----------

def load_full_prompt() -> str:
    if not PROMPT_PATH.is_file():
        print(f"[ERROR] Не найден файл промпта: {PROMPT_PATH}", file=sys.stderr)
        sys.exit(1)
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_answer(raw: str) -> str:
    """
    Пытаемся вытащить поле `answer` из JSON.
    Если не получается — обрезаем технический мусор и возвращаем «чистый» текст.
    """
    raw = raw.strip()

    # 1) Попробуем найти JSON-блок по фигурным скобкам
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = raw[first_brace:last_brace + 1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "answer" in data:
                return str(data["answer"]).strip()
        except Exception:
            # Падать не будем — просто пойдём дальше
            pass

    # 2) Если JSON не удалось распарсить, обрежем технический хвост
    cut_tokens = [
        "<extra_id_",  # служебные токены
        "```",         # возможные блоки кода/JSON
        "\nUser:",     # самопридуманные продолжения диалога
        "\n<|",        # разделители некоторых форматов
    ]
    cleaned = raw
    for token in cut_tokens:
        idx = cleaned.find(token)
        if idx != -1:
            cleaned = cleaned[:idx]

    return cleaned.strip()


def build_messages(system_prompt: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Собираем список сообщений для create_chat_completion.
    history — список словарей вида {"role": "user"/"assistant", "content": "..."}.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(history)
    return messages


# ---------- Инициализация LLM ----------

def init_llm() -> Llama:
    if not MODEL_PATH.is_file():
        print(f"[ERROR] Не найден файл модели: {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Загружаю модель LLM из: {MODEL_PATH}")
    # Увеличиваем контекст до 8192, чтобы не было ошибки про 4096
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=8192,
        n_gpu_layers=-1,   # использовать все доступные слои на GPU
        seed=42,
        logits_all=False,
        vocab_only=False,
        use_mmap=True,
        use_mlock=False,
        n_batch=512,
        f16_kv=True,
        verbose=False,
    )
    return llm


# ---------- Основной цикл диалога ----------

def chat_loop():
    system_prompt = load_full_prompt()
    llm = init_llm()

    print("=== Текстовый тест Аси на локальной LLM ===")
    print(f"Модель:       {MODEL_PATH}")
    print(f"Файл промпта: {PROMPT_PATH}")
    print("Команды: /exit — выход, /reset — сброс диалога\n")

    # История диалога (без system)
    history: List[Dict[str, str]] = []

    while True:
        try:
            user_text = input("Клиент: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not user_text:
            continue

        if user_text.lower() in ("/exit", "exit", "quit"):
            print("Завершение работы.")
            break

        if user_text.lower() in ("/reset", "reset"):
            history.clear()
            print("Диалог сброшен.\n")
            continue

        # Добавляем реплику клиента в историю
        history.append({"role": "user", "content": user_text})

        # Чтобы не раздувать контекст, ограничим историю последними N репликами
        # (например, 6 сообщений: user/assistant попеременно)
        if len(history) > 6:
            history = history[-6:]

        messages = build_messages(system_prompt, history)

        try:
            result = llm.create_chat_completion(
                messages=messages,
                max_tokens=256,
                temperature=0.1,
                top_p=0.9,
                repeat_penalty=1.1,
            )
        except Exception as e:
            print(f"[ERROR] Ошибка при обращении к LLM: {e}")
            # Удалим последнюю реплику, чтобы не копить мусор
            history.pop()
            continue

        raw = result["choices"][0]["message"]["content"]
        answer = extract_answer(raw)

        print(f"Ася: {answer}\n")

        # Сохраняем в историю уже очищенный ответ
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    chat_loop()
