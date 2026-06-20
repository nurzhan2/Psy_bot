"""
Скрипт построения векторных индексов.
Запускать вручную после того, как материалы появились в папках:
  python -m app.rag.build_index

Личные материалы (personal_materials) и книги (books) индексируются
отдельно — это нужно, чтобы при поиске сначала проверять "золотой фонд"
автора методики, и только потом — общую теоретическую базу.
"""
from app.rag.loader import load_directory
from app.rag.vector_store import VectorStore
from config import PERSONAL_MATERIALS_DIR, BOOKS_DIR


def main():
    print("Загружаю личные материалы...")
    personal_chunks = load_directory(PERSONAL_MATERIALS_DIR, category="personal")
    print(f"  найдено чанков: {len(personal_chunks)}")

    print("Загружаю материалы из books (конспекты/легальные источники)...")
    book_chunks = load_directory(BOOKS_DIR, category="books")
    print(f"  найдено чанков: {len(book_chunks)}")

    print("Строю индекс personal...")
    personal_store = VectorStore("personal")
    personal_store.build(personal_chunks)

    print("Строю индекс books...")
    books_store = VectorStore("books")
    books_store.build(book_chunks)

    print("Готово. Индексы сохранены в data/index/")


if __name__ == "__main__":
    main()
