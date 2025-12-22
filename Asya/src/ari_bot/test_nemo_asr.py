import os
from pathlib import Path

import torch
import soundfile as sf

from nemo.collections.asr.models import EncDecCTCModelBPE

CALL_RECORDS_DIR = Path(__file__).parent / "call_records"


def get_duration_sec(path: Path) -> float:
    """Грубая проверка длительности файла."""
    try:
        data, sr = sf.read(path)
        if data.ndim > 1:
            # стерео -> моно
            data = data.mean(axis=1)
        return float(len(data)) / float(sr)
    except Exception as e:
        print(f"  [SKIP] Не удалось прочитать {path.name}: {e}")
        return 0.0


def main():
    print("=== NeMo ASR тест ===")

    print(f"PyTorch: {torch.__version__} CUDA available: {torch.cuda.is_available()}")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if not CALL_RECORDS_DIR.exists():
        print(f"Папка с записями не найдена: {CALL_RECORDS_DIR}")
        return

    wav_paths = sorted(CALL_RECORDS_DIR.glob("*.wav"))
    if not wav_paths:
        print(f"В {CALL_RECORDS_DIR} нет .wav файлов")
        return

    print("Найдены файлы:")
    for p in wav_paths:
        print(f"  {p} (size={p.stat().st_size} bytes)")

    # Отфильтруем заведомо пустые/битые записи
    valid_paths = []
    print("\nПроверяем длительность файлов...")
    for p in wav_paths:
        dur = get_duration_sec(p)
        print(f"  {p.name}: duration ~ {dur:.3f} c")
        if dur < 0.2:
            print(f"    [SKIP] Слишком короткий (< 0.2 c), пропускаем")
        else:
            valid_paths.append(p)

    if not valid_paths:
        print("\nНет ни одной записи с достаточной длительностью. "
              "Сделай новый звонок и поговори хотя бы 5–10 секунд.")
        return

    print("\nЗагружаем модель NeMo: stt_ru_conformer_ctc_large ...")
    asr_model = EncDecCTCModelBPE.from_pretrained("nvidia/stt_ru_conformer_ctc_large")
    asr_model.to(device)
    asr_model.eval()
    print("Модель загружена и переведена на", device)

    # NeMo ожидает список строк-путей
    paths_str = [str(p) for p in valid_paths]

    print("\nЗапускаем распознавание...")
    with torch.no_grad():
        texts = asr_model.transcribe(paths_str, batch_size=1)

    print("\n=== Результаты распознавания ===")
    for path, text in zip(valid_paths, texts):
        print(f"{path.name} -> \"{text}\"")


if __name__ == "__main__":
    main()
