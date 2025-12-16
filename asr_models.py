import nemo.collections.asr as nemo_asr
import os
import sys

def main():
    print("🎯 Загрузка модели для русского языка...")
    
    try:
        # Загрузка модели
        asr_model = nemo_asr.models.ASRModel.from_pretrained("stt_ru_fastconformer_hybrid_large_pc")
        print("✅ Модель загружена успешно!")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        print("\n💡 Возможные решения:")
        print("1. Проверьте установку NeMo: pip install nemo_toolkit")
        print("2. Установите недостающие зависимости")
        return

    # Укажите путь к вашему аудиофайлу
    audio_path = r"C:\Users\Ekaterina.Simonova\Downloads\Ася\real_call_mono.wav"
    
    # Проверка существования файла
    if not os.path.exists(audio_path):
        print(f"❌ Файл не найден: {audio_path}")
        print("💡 Убедитесь, что:")
        print("   - Файл существует по указанному пути")
        print("   - Файл преобразован в моно-формат (16 кГц)")
        print("   - Указан правильный путь")
        return

    print(f"🎧 Найден файл: {audio_path}")
    
    try:
        # Транскрибация
        print("🎤 Выполняю транскрибацию...")
        result = asr_model.transcribe([audio_path])
        
        # Вывод результата
        print("\n" + "="*70)
        print("📝 РЕЗУЛЬТАТ ТРАНСКРИБАЦИИ:")
        print("="*70)
        print(result[0])
        print("="*70)
        
        # Сохранение в файл
        output_file = "transcription_result.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(str(result[0]))
        print(f"💾 Результат сохранен в файл: {output_file}")
        
    except Exception as e:
        print(f"❌ Ошибка транскрибации: {e}")

if __name__ == "__main__":
    main()