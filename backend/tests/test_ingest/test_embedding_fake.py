"""Đơn vị cho FakeEmbeddingAdapter (D6/D8, phase-2.md): tất định, đúng số chiều, không gọi mạng."""

from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter


async def test_same_text_always_gives_same_vector() -> None:
    adapter = FakeEmbeddingAdapter()

    first = await adapter.embed(["nghỉ phép năm"])
    second = await adapter.embed(["nghỉ phép năm"])

    assert first == second


async def test_different_texts_give_different_vectors() -> None:
    adapter = FakeEmbeddingAdapter()

    vectors = await adapter.embed(["văn bản một", "văn bản hai hoàn toàn khác"])

    assert vectors[0] != vectors[1]


async def test_vector_dimension_is_1024() -> None:
    adapter = FakeEmbeddingAdapter()

    [vector] = await adapter.embed(["bất kỳ"])

    assert len(vector) == 1024
    assert adapter.dimension == 1024


async def test_empty_texts_list_returns_empty_list() -> None:
    adapter = FakeEmbeddingAdapter()

    assert await adapter.embed([]) == []


async def test_preserves_order_of_input_texts() -> None:
    adapter = FakeEmbeddingAdapter()
    texts = ["a", "b", "c"]

    vectors = await adapter.embed(texts)
    individually = [(await adapter.embed([t]))[0] for t in texts]

    assert vectors == individually
