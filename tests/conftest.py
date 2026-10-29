import pytest

from cite_or_refuse.corpus import Corpus
from cite_or_refuse.retriever import Retriever


@pytest.fixture(scope="session")
def corpus():
    return Corpus.load()


@pytest.fixture(scope="session")
def retriever(corpus):
    return Retriever(corpus)


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    # Tests always exercise the deterministic path unless a test opts in.
    monkeypatch.delenv("COR_LLM_MODEL", raising=False)
    monkeypatch.delenv("COR_LLM_JUDGE", raising=False)
