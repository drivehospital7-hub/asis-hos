"""Tests for genderize_verifier — focuses on nombres_no_cache in get_stats()."""
from unittest.mock import patch

from app.services.genderize_extractor import ExtractResult
from app.services.genderize_verifier import get_stats


class TestGetStatsNombresNoCache:
    """Tests for nombres_no_cache return value from get_stats().

    Expected behavior:
    - Tercer elemento es list[str] con compound_name de los que NO están en cache
    - Preserva el orden de aparición en el archivo (orden de facturas)
    - compound_name: "primer_nombre segundo_nombre" si hay segundo_nombre, sino solo primer_nombre
    """

    # ── fixtures ──────────────────────────────────────────────────────

    @staticmethod
    def _make_result(
        factura: str,
        primer_nombre: str,
        segundo_nombre: str = "",
        nombre_normalizado: str | None = None,
    ) -> ExtractResult:
        if nombre_normalizado is None:
            nfd = __import__("unicodedata").normalize("NFD",
                f"{primer_nombre} {segundo_nombre}".strip() if segundo_nombre else primer_nombre)
            sin_tilde = "".join(c for c in nfd if __import__("unicodedata").category(c) != "Mn")
            nombre_normalizado = sin_tilde.lower().strip()
        return ExtractResult(
            numero_factura=factura,
            primer_apellido="Apellido",
            segundo_apellido="",
            primer_nombre=primer_nombre,
            segundo_nombre=segundo_nombre,
            nombre_completo=f"Apellido {primer_nombre} {segundo_nombre}".strip(),
            sexo="M",
            nombre_normalizado=nombre_normalizado,
        )

    @staticmethod
    def _mock_session(mock_data, mock_cache):
        """Context manager that patches both extractor and cache."""
        return (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo",
                  return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache",
                  return_value=mock_cache),
        )

    # ── Test data fixtures ────────────────────────────────────────────

    @property
    def sample_results(self):
        """5 facturas: Nicolas, Johan Matias, Angela, Emilin Sofia, Derly."""
        return [
            self._make_result("FAC-001", "Nicolas"),
            self._make_result("FAC-002", "Johan", "Matias"),
            self._make_result("FAC-003", "Angela"),
            self._make_result("FAC-004", "Emilin", "Sofia"),
            self._make_result("FAC-005", "Derly"),
        ]

    @property
    def cache_with_nicolas_angela(self):
        return {
            "nicolas": {"gender": "male", "probability": 0.99},
            "angela": {"gender": "female", "probability": 0.95},
        }

    @property
    def cache_all_five(self):
        return {
            "nicolas": {"gender": "male", "probability": 0.99},
            "johan matias": {"gender": "male", "probability": 0.99},
            "angela": {"gender": "female", "probability": 0.95},
            "emilin sofia": {"gender": "female", "probability": 0.95},
            "derly": {"gender": "female", "probability": 0.95},
        }

    @property
    def cache_empty(self):
        return {}

    # ── Scenario: Partial cache miss ──────────────────────────────────

    def test_partial_cache_miss_returns_uncached_compound_names(self):
        """GIVEN partial cache (2/5 cached), WHEN get_stats, THEN nombres_no_cache has 3 names."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_with_nicolas_angela)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert isinstance(nombres_no_cache, list)
        assert all(isinstance(n, str) for n in nombres_no_cache)
        assert stats.api_calls_necesarias == len(nombres_no_cache)
        # nicolas + angela cached → missing: Johan Matias, Emilin Sofia, Derly
        assert nombres_no_cache == ["Johan Matias", "Emilin Sofia", "Derly"]

    # ── Scenario: All names cached ────────────────────────────────────

    def test_all_cached_returns_empty_list(self):
        """GIVEN all names cached, WHEN get_stats, THEN nombres_no_cache is []."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_all_five)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert isinstance(nombres_no_cache, list)
        assert len(nombres_no_cache) == 0
        assert stats.cache_hits == 5
        assert stats.api_calls_necesarias == 0

    # ── Scenario: No names cached ─────────────────────────────────────

    def test_none_cached_returns_all_names(self):
        """GIVEN empty cache, WHEN get_stats, THEN nombres_no_cache has all 5 names."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_empty)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert isinstance(nombres_no_cache, list)
        assert len(nombres_no_cache) == 5
        assert stats.api_calls_necesarias == 5
        assert nombres_no_cache == [
            "Nicolas", "Johan Matias", "Angela", "Emilin Sofia", "Derly",
        ]

    # ── Return type: 3-element tuple ──────────────────────────────────

    def test_return_is_three_element_tuple(self):
        """GIVEN get_stats, WHEN called, THEN result is a 3-tuple with list[str] as 3rd."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_all_five)
        with p1, p2:
            result = get_stats("dummy.xlsx")

        assert len(result) == 3
        assert isinstance(result[0].__class__.__name__, str)  # Stats
        assert isinstance(result[1], dict)                     # facturas
        assert isinstance(result[2], list)                     # nombres_no_cache
