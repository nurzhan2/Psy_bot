"""
Векторное хранилище на FAISS (Facebook AI Similarity Search) — библиотека для
быстрого поиска похожих векторов. Хранит embeddings (числовые представления
смысла текста) отдельно для двух категорий: personal (приоритет 1) и books (приоритет 2),
в соответствии с требованиями клиентки по приоритетности источников.
"""
import os
import pickle
from typing import List, Tuple

import faiss
import numpy as np
from openai import OpenAI

from config import OPENAI_API_KEY, EMBEDDING_MODEL, INDEX_DIR
from app.rag.loader import Chunk
from app import llm_optimize

client = OpenAI(api_key=OPENAI_API_KEY)


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Получает embeddings для списка текстов через OpenAI API.
    Блок 4: сначала смотрим кэш (хэш контента -> вектор), к API обращаемся
    только за промахами — это экономит повторное эмбеддирование при пересборке
    индекса. Сбой кэша не критичен: при любой ошибке падаем на прямой вызов API.
    """
    vectors: List = [None] * len(texts)
    missing_idx: List[int] = []
    missing_texts: List[str] = []

    for i, t in enumerate(texts):
        cached = llm_optimize.get_cached_embedding(t, EMBEDDING_MODEL)
        if cached is not None:
            vectors[i] = cached
        else:
            missing_idx.append(i)
            missing_texts.append(t)

    if missing_texts:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=missing_texts)
        for j, item in enumerate(response.data):
            emb = item.embedding
            idx = missing_idx[j]
            vectors[idx] = emb
            llm_optimize.store_embedding(missing_texts[j], EMBEDDING_MODEL, emb)

    return np.array(vectors, dtype="float32")


class VectorStore:
    def __init__(self, name: str):
        self.name = name
        self.index_path = os.path.join(INDEX_DIR, f"{name}.faiss")
        self.meta_path = os.path.join(INDEX_DIR, f"{name}.pkl")
        self.index = None
        self.chunks: List[Chunk] = []

    def build(self, chunks: List[Chunk], batch_size: int = 100):
        os.makedirs(INDEX_DIR, exist_ok=True)
        if not chunks:
            self.chunks = []
            self.index = faiss.IndexFlatIP(1536)  # размерность text-embedding-3-small
            self._save()
            return

        all_vectors = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            vectors = embed_texts([c.text for c in batch])
            # нормализация для косинусного сходства через inner product
            faiss.normalize_L2(vectors)
            all_vectors.append(vectors)

        matrix = np.vstack(all_vectors)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)

        self.index = index
        self.chunks = chunks
        self._save()

    def _save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self) -> bool:
        if not os.path.exists(self.index_path) or not os.path.exists(self.meta_path):
            return False
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            self.chunks = pickle.load(f)
        return True

    def search(self, query: str, top_k: int) -> List[Tuple[Chunk, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vec = embed_texts([query])
        faiss.normalize_L2(query_vec)
        scores, indices = self.index.search(query_vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results
