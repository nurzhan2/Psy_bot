"""
Расшифровка АВТОРСКИХ аудио-практик Екатерины (не голосовых от пользователей!)
в текст для добавления в personal_materials/.

Это другой случай, чем app/handlers/voice.py — там про голос ПОЛЬЗОВАТЕЛЕЙ,
который нужно удалять сразу после распознавания. Здесь — собственные
медитации Екатерины, которые осознанно становятся частью базы знаний и
МОГУТ храниться (сам .mp3 можно не хранить после расшифровки, но это уже
по желанию — юридических ограничений на это, в отличие от голоса клиентов, нет).

Запуск:
  python tools/transcribe_audio.py personal_materials/audio_raw/Медитация_Денежное_древо_рода_.mp3
Результат сохранится рядом, с тем же именем и расширением .txt, прямо в
personal_materials/, чтобы потом попасть в индекс через build_index.

Если файлов несколько — можно передать путь к папке:
  python tools/transcribe_audio.py personal_materials/audio_raw/
"""
import sys
from pathlib import Path

from openai import OpenAI

from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".wav", ".oga"}


def transcribe_file(audio_path: Path, output_dir: Path):
    print(f"Расшифровываю: {audio_path.name} ...")
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ru",
        )

    output_path = output_dir / (audio_path.stem + ".txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript.text)

    print(f"  -> сохранено: {output_path}")


def main(path_str: str):
    path = Path(path_str)

    if path.is_dir():
        files = [p for p in path.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS]
        if not files:
            print(f"В папке {path} не найдено аудиофайлов.")
            return
        # сохраняем расшифровки в personal_materials/ (на уровень выше audio_raw/),
        # чтобы build_index их подхватил
        output_dir = path.parent
        for f in files:
            transcribe_file(f, output_dir)
    else:
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            print(f"Неподдерживаемый формат: {path.suffix}")
            return
        transcribe_file(path, path.parent.parent)  # из audio_raw/ -> в personal_materials/

    print("\nГотово. Не забудь пересобрать индекс:")
    print("  python -m app.rag.build_index")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python transcribe_audio.py <файл.mp3 или папка>")
        sys.exit(1)
    main(sys.argv[1])
