"""Normalize numeric and ordinal selector words without parsing references."""

from __future__ import annotations

from functools import lru_cache

from pymorphy3 import MorphAnalyzer


_ORDINAL_NUMBERS = {
    "первый": 1, "второй": 2, "третий": 3, "четвертый": 4,
    "пятый": 5, "шестой": 6, "седьмой": 7, "восьмой": 8,
    "девятый": 9, "десятый": 10, "одиннадцатый": 11,
    "двенадцатый": 12, "тринадцатый": 13, "четырнадцатый": 14,
    "пятнадцатый": 15, "шестнадцатый": 16, "семнадцатый": 17,
    "восемнадцатый": 18, "девятнадцатый": 19, "двадцатый": 20,
    "тридцатый": 30, "сороковой": 40, "пятидесятый": 50,
    "шестидесятый": 60, "семидесятый": 70, "восьмидесятый": 80,
    "девяностый": 90, "сотый": 100,
    "тысячный": 1_000, "миллионный": 1_000_000,
    "миллиардный": 1_000_000_000, "триллионный": 1_000_000_000_000,
}
_CARDINAL_NUMBERS = {
    "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2,
    "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7,
    "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
    "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
    "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
    "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20,
    "тридцать": 30, "сорок": 40, "пятьдесят": 50,
    "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80,
    "девяносто": 90, "сто": 100, "двести": 200, "триста": 300,
    "четыреста": 400, "пятьсот": 500, "шестьсот": 600,
    "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
    "тысяча": 1_000, "миллион": 1_000_000, "миллиард": 1_000_000_000,
    "триллион": 1_000_000_000_000,
}
_COMPOUND_CARDINAL_PREFIXES = {
    "двух": 2, "трех": 3, "четырех": 4, "пяти": 5,
    "шести": 6, "семи": 7, "восьми": 8, "девяти": 9,
    "десяти": 10, "одиннадцати": 11, "двенадцати": 12,
    "тринадцати": 13, "четырнадцати": 14, "пятнадцати": 15,
    "шестнадцати": 16, "семнадцати": 17, "восемнадцати": 18,
    "девятнадцати": 19, "двадцати": 20, "тридцати": 30,
    "сорока": 40, "пятидесяти": 50, "шестидесяти": 60,
    "семидесяти": 70, "восьмидесяти": 80, "девяноста": 90,
    "ста": 100,
}
_ORDINAL_NUMBERS.update({
    f"{prefix}сотый": value * 100
    for prefix, value in (("двух", 2), ("трех", 3), ("четырех", 4),
                          ("пяти", 5), ("шести", 6), ("семи", 7),
                          ("восьми", 8), ("девяти", 9))
})


class NumberNormalizer:
    """Convert supported inflected Russian number phrases to integers."""

    def __init__(self, morphology: MorphAnalyzer):
        self._morphology = morphology

    @lru_cache(maxsize=32768)
    def is_ordinal(self, value: str) -> bool:
        """Recognize ordinal word forms without choosing a ranked parse."""
        return any(parse.tag.POS == "NUMR" or "Anum" in str(parse.tag)
                   for parse in self._morphology.parse(value))

    @lru_cache(maxsize=32768)
    def ordinal_number(self, value: str) -> int | None:
        """Return an ordinal value from its inflected or compositional lemma."""
        for parse in self._morphology.parse(value):
            if parse.tag.POS == "NUMR" or "Anum" in str(parse.tag):
                lemma = parse.normal_form.replace("ё", "е")
                number = _ORDINAL_NUMBERS.get(lemma)
                if number is not None:
                    return number
                for suffix, scale in (("тысячный", 1_000),
                                      ("миллионный", 1_000_000),
                                      ("миллиардный", 1_000_000_000),
                                      ("триллионный", 1_000_000_000_000)):
                    if lemma.endswith(suffix):
                        coefficient = _COMPOUND_CARDINAL_PREFIXES.get(
                            lemma[:-len(suffix)])
                        if coefficient is not None:
                            return coefficient * scale
        return None

    @lru_cache(maxsize=32768)
    def cardinal_number(self, value: str) -> int | None:
        """Return the value of a supported cardinal word form."""
        for parse in self._morphology.parse(value):
            number = _CARDINAL_NUMBERS.get(parse.normal_form.replace("ё", "е"))
            if number is not None:
                return number
        return None

    @lru_cache(maxsize=32768)
    def ordinal_phrase_number(self, values: tuple[str, ...]) -> int | None:
        """Convert a cardinal prefix plus a final ordinal into one integer."""
        if len(values) < 2:
            return None
        lemmas = []
        for value in values:
            lemma = next((parse.normal_form.replace("ё", "е")
                          for parse in self._morphology.parse(value)
                          if parse.tag.POS in {"NUMR", "ADJF", "NOUN"}), None)
            if lemma is None:
                return None
            lemmas.append(lemma)
        final = _ORDINAL_NUMBERS.get(lemmas[-1])
        if final is None:
            return None
        prefix = [_CARDINAL_NUMBERS.get(lemma) for lemma in lemmas[:-1]]
        if any(number is None for number in prefix):
            return None
        total = current = 0
        previous = 10**15
        previous_scale = 10**15
        for number in prefix:
            if number >= 1_000:
                if number >= previous_scale:
                    return None
                total += max(current, 1) * number
                current = 0
                previous = 10**15
                previous_scale = number
            else:
                if number >= previous:
                    return None
                current += number
                previous = number
        return total + current + final
