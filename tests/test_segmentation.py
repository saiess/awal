import pytest

from app.segmentation import segment_text


@pytest.mark.parametrize("text", [
    'Dr. Smith measured 3.14 meters. "Really?" she asked. Yes!\n\nNASA uses a U.S. lab.',
    "\r\n\r\nHello, world.\r\n\r\nUnicode: café, naïve, Ouarzazate — and quotes “like this.”",
    "A very long sentence, " * 80 + "ends here.",
    "x" * 901,
    "Short.",
])
def test_preserves_order_punctuation_and_bounds(text):
    result = segment_text(text, 100)
    assert all(0 < len(s) <= 100 for s in result)
    assert "".join("".join(result).split()) == "".join(text.split())


def test_abbreviation_decimal_and_quoted_sentence():
    result = segment_text('Dr. Smith measures 3.14. "A complete sentence!" Then we return.', 44)
    assert result[0] == "Dr. Smith measures 3.14."
    assert result[1] == '"A complete sentence!" Then we return.'


@pytest.mark.parametrize("text", ["", " \n\n ", "... ! ?"])
def test_empty_script_rejected(text):
    with pytest.raises(ValueError): segment_text(text)
