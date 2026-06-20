"""
Загрузка документов (txt/pdf) из папок personal_materials и books,
разбиение на чанки для последующей индексации.
"""
import os
from dataclasses import dataclass
from typing import List

from pypdf import PdfReader


@dataclass
class Chunk:
    text: str
    source: str          # имя файла
    category: str        # "personal" или "books"


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_pdf(path: str) -> str:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def load_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt" or ext == ".md":
        return _read_txt(path)
    if ext == ".pdf":
        return _read_pdf(path)
    raise ValueError(f"Неподдерживаемый формат файла: {path}")


def split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """
    Простое разбиение по символам с перекрытием (overlap), чтобы не терять
    смысл на границах кусков. Для старта этого достаточно; позже можно
    заменить на разбиение по предложениям/абзацам.
    """
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def load_directory(directory: str, category: str) -> List[Chunk]:
    """
    Проходит по всем файлам в директории (рекурсивно) и возвращает список чанков.
    """
    result: List[Chunk] = []
    if not os.path.isdir(directory):
        return result

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.startswith("."):
                continue
            path = os.path.join(root, filename)
            try:
                text = load_file(path)
            except ValueError:
                continue
            for chunk_text in split_into_chunks(text):
                result.append(Chunk(text=chunk_text, source=filename, category=category))
    return result
