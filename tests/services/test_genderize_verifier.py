"""Tests for genderize_verifier — get_stats() and verificar_y_comparar()."""
from unittest.mock import patch

from app.services.genderize_extractor import ExtractResult
from app.services.genderize_verifier import get_stats, verificar_y_comparar, Discrepancia


class TestGetStatsNombresNoCache:
    """Tests for nombres_no_cache return value from get_stats().

    Expected behavior:
    - Tercer elemento es list[dict] con {"nombre": str, "sexo": str}
    - Preserva el orden de aparición en el archivo (orden de facturas)
    - sexo viene del campo sexo de ExtractResult
    - api_calls_necesarias = unique_names - cache_hits (cantidad sin cache)
    """

    # ── fixtures ──────────────────────────────────────────────────────

    @staticmethod
    def _make_result(
        factura: str,
        primer_nombre: str,
        segundo_nombre: str = "",
        sexo: str = "M",
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
            sexo=sexo,
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

    def test_partial_cache_miss_returns_list_of_dicts(self):
        """GIVEN partial cache (2/5 cached), WHEN get_stats, THEN nombres_no_cache has 3 dicts with nombre+sexo."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_with_nicolas_angela)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert isinstance(nombres_no_cache, list)
        assert len(nombres_no_cache) == 3
        for entry in nombres_no_cache:
            assert isinstance(entry, dict)
            assert "nombre" in entry
            assert "sexo" in entry
        assert stats.api_calls_necesarias == 3  # 5 unique - 2 cache hits
        # nicolas + angela cached → missing: johan matias, emilin sofia, derly
        assert [e["nombre"] for e in nombres_no_cache] == ["johan matias", "emilin sofia", "derly"]
        assert all(e["sexo"] == "M" for e in nombres_no_cache)

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
        """GIVEN empty cache, WHEN get_stats, THEN nombres_no_cache has all 5 dicts."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_empty)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert isinstance(nombres_no_cache, list)
        assert len(nombres_no_cache) == 5
        assert stats.api_calls_necesarias == 5  # 5 unique - 0 cache hits
        assert [e["nombre"] for e in nombres_no_cache] == [
            "nicolas", "johan matias", "angela", "emilin sofia", "derly",
        ]
        assert all(e["sexo"] == "M" for e in nombres_no_cache)

    # ── Scenario: "Hijo de"/"Hija de" excluded ────────────────────────

    @property
    def sample_with_hijo_de(self):
        """3 normales + 2 "Hijo de"/"Hija de"."""
        return self.sample_results + [
            self._make_result("FAC-006", "Hijo de", "Juan"),
            self._make_result("FAC-007", "Hija de", "Maria"),
        ]

    def test_hijo_de_excluded_from_nombres_no_cache(self):
        """GIVEN Hijo de/Hija de names, WHEN get_stats, THEN excluded from nombres_no_cache."""
        results = self.sample_with_hijo_de
        cache = {"johan matias": {"gender": "male", "probability": 0.99}}
        p1, p2 = self._mock_session(results, cache)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert stats.nombres_unicos == 7
        assert stats.cache_hits == 1
        assert stats.api_calls_necesarias == 4  # 7 unique - 1 cache hit - 2 hijo/hija = 4
        nombres = [e["nombre"] for e in nombres_no_cache]
        assert "hijo de juan" not in nombres
        assert "hija de maria" not in nombres

    # ── Scenario: Sexo values preserved from Excel ────────────────────

    def test_sexo_from_excel_preserved(self):
        """GIVEN facturas with different sexo values, WHEN get_stats, THEN sexo matches Excel."""
        results = [
            self._make_result("FAC-001", "Maria", sexo="F"),
            self._make_result("FAC-002", "Carlos", sexo="M"),
            self._make_result("FAC-003", "Luisa", sexo="F"),
        ]
        p1, p2 = self._mock_session(results, self.cache_empty)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert len(nombres_no_cache) == 3
        assert nombres_no_cache[0] == {"nombre": "maria", "sexo": "F"}
        assert nombres_no_cache[1] == {"nombre": "carlos", "sexo": "M"}
        assert nombres_no_cache[2] == {"nombre": "luisa", "sexo": "F"}

    # ── Deduplication by nombre_normalizado ────────────────────────────

    def test_deduplicates_by_nombre_normalizado(self):
        """GIVEN same normalized name across facturas, WHEN get_stats, THEN only one entry."""
        results = [
            self._make_result("FAC-001", "Juan"),
            self._make_result("FAC-002", "Juan"),  # same name, different factura
        ]
        p1, p2 = self._mock_session(results, self.cache_empty)
        with p1, p2:
            stats, facturas, nombres_no_cache = get_stats("dummy.xlsx")

        assert len(nombres_no_cache) == 1
        assert nombres_no_cache[0] == {"nombre": "juan", "sexo": "M"}

    # ── Return type: 3-element tuple ──────────────────────────────────

    def test_return_is_three_element_tuple(self):
        """GIVEN get_stats, WHEN called, THEN result is a 3-tuple with list[dict] as 3rd."""
        p1, p2 = self._mock_session(self.sample_results, self.cache_all_five)
        with p1, p2:
            result = get_stats("dummy.xlsx")

        assert len(result) == 3
        assert isinstance(result[0].__class__.__name__, str)  # Stats
        assert isinstance(result[1], dict)                     # facturas
        assert isinstance(result[2], list)                     # nombres_no_cache


# ── verificar_y_comparar: 4-value mapping ──────────────────────────────

class TestVerificarYComparar4Valores:
    """Tests for verificar_y_comparar with 4-value mapping (F/M/L/U), sin API."""

    @staticmethod
    def _make_result(
        factura: str,
        primer_nombre: str,
        sexo: str = "M",
        nombre_normalizado: str | None = None,
        segundo_nombre: str = "",
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
            nombre_completo=f"Apellido {primer_nombre}",
            sexo=sexo,
            nombre_normalizado=nombre_normalizado,
        )

    def test_undefined_shows_as_U(self):
        """GIVEN sexo_excel='M' and sexo_api='undefined', WHEN verificar, THEN discrepancia.sexo_api='U'."""
        mock_data = [self._make_result("FAC-001", "Juan", sexo="M")]
        mock_cache = {"juan": {"gender": "undefined", "probability": 0.0, "count": 0}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_api == "U"
        assert stats.api_calls_necesarias == 0

    def test_lastname_shows_as_L(self):
        """GIVEN sexo_excel='F' and sexo_api='lastname', WHEN verificar, THEN discrepancia.sexo_api='L'."""
        mock_data = [self._make_result("FAC-002", "Maria", sexo="F")]
        mock_cache = {"maria": {"gender": "lastname", "probability": 0.0, "count": 0}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_api == "L"
        assert stats.api_calls_necesarias == 0

    def test_male_shows_as_M(self):
        """GIVEN sexo_excel='F' and sexo_api='male', WHEN verificar, THEN discrepancia.sexo_api='M'."""
        mock_data = [self._make_result("FAC-003", "Pedro", sexo="F")]
        mock_cache = {"pedro": {"gender": "male", "probability": 0.99, "count": 100}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_api == "M"
        assert stats.api_calls_necesarias == 0

    def test_female_shows_as_F(self):
        """GIVEN sexo_excel='M' and sexo_api='female', WHEN verificar, THEN discrepancia.sexo_api='F'."""
        mock_data = [self._make_result("FAC-004", "Ana", sexo="M")]
        mock_cache = {"ana": {"gender": "female", "probability": 0.95, "count": 50}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_api == "F"
        assert stats.api_calls_necesarias == 0

    def test_matching_sexo_no_discrepancy(self):
        """GIVEN sexo_excel='M' and sexo_api='male', WHEN verificar, THEN no discrepancies."""
        mock_data = [self._make_result("FAC-005", "Carlos", sexo="M")]
        mock_cache = {"carlos": {"gender": "male", "probability": 0.99, "count": 100}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.api_calls_necesarias == 0

    def test_sexo_excel_is_preserved_in_discrepancy(self):
        """GIVEN sexo_excel='F' and sexo_api='male', WHEN verificar, THEN discrepancia.sexo_excel='F'."""
        mock_data = [self._make_result("FAC-006", "Luisa", sexo="F")]
        mock_cache = {"luisa": {"gender": "male", "probability": 0.99, "count": 100}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_excel == "F"
        assert discrepancies[0].sexo_api == "M"
        assert stats.api_calls_necesarias == 0

    def test_non_cached_name_skipped(self):
        """GIVEN name not in cache, WHEN verificar, THEN no discrepancy (skip silently)."""
        mock_data = [self._make_result("FAC-007", "Pedro", sexo="M")]
        mock_cache = {}  # empty cache
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.cache_hits == 0
        assert stats.api_calls_necesarias == 1  # 1 unique - 0 cache hits

    # ── "Hijo de"/"Hija de" forced gender ──────────────────────────────

    def test_hijo_de_matching_sexo_no_discrepancy(self):
        """GIVEN 'Hijo de' with sexo_excel='M', WHEN verificar, THEN no discrepancy."""
        mock_data = [
            self._make_result("FAC-010", "Hijo de", sexo="M", segundo_nombre="Juan"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.api_calls_necesarias == 0  # forced name excluded from API count

    def test_hijo_de_mismatching_sexo_creates_discrepancy(self):
        """GIVEN 'Hijo de' with sexo_excel='F', WHEN verificar, THEN discrepancy (expected M)."""
        mock_data = [
            self._make_result("FAC-011", "Hijo de", sexo="F", segundo_nombre="Juan"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_excel == "F"
        assert discrepancies[0].sexo_api == "M"
        assert "hijo de juan" in discrepancies[0].nombre_normalizado

    def test_hija_de_matching_sexo_no_discrepancy(self):
        """GIVEN 'Hija de' with sexo_excel='F', WHEN verificar, THEN no discrepancy."""
        mock_data = [
            self._make_result("FAC-012", "Hija de", sexo="F", segundo_nombre="Maria"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.api_calls_necesarias == 0  # forced name excluded from API count

    def test_hija_de_mismatching_sexo_creates_discrepancy(self):
        """GIVEN 'Hija de' with sexo_excel='M', WHEN verificar, THEN discrepancy (expected F)."""
        mock_data = [
            self._make_result("FAC-013", "Hija de", sexo="M", segundo_nombre="Maria"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 1
        assert discrepancies[0].sexo_excel == "M"
        assert discrepancies[0].sexo_api == "F"
        assert "hija de maria" in discrepancies[0].nombre_normalizado

    def test_hijo_de_full_primer_nombre_matching(self):
        """GIVEN 'HIJO DE DARIANA' in primer_nombre (no segundo_nombre), WHEN verificar, THEN no discrepancy."""
        mock_data = [
            self._make_result("FAC-014", "HIJO DE DARIANA", sexo="M"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.api_calls_necesarias == 0

    def test_hija_de_full_primer_nombre_matching(self):
        """GIVEN 'HIJA DE MARIA' in primer_nombre (no segundo_nombre), WHEN verificar, THEN no discrepancy."""
        mock_data = [
            self._make_result("FAC-015", "HIJA DE MARIA", sexo="F"),
        ]
        mock_cache = {}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        assert len(discrepancies) == 0
        assert stats.api_calls_necesarias == 0

    def test_mixed_forced_cache_and_miss_stats(self):
        """GIVEN forced + cache hit + cache miss, THEN only forced + cache hit checked, stats correct."""
        mock_data = [
            self._make_result("FAC-020", "Ana", sexo="M"),
            self._make_result("FAC-021", "Pedro", sexo="M"),
            self._make_result("FAC-022", "Hijo de", sexo="M", segundo_nombre="Luis"),
            self._make_result("FAC-023", "Hija de", sexo="F", segundo_nombre="Laura"),
        ]
        mock_cache = {"ana": {"gender": "female", "probability": 0.95, "count": 50}}
        with (
            patch("app.services.genderize_verifier.extract_factura_nombre_sexo", return_value=mock_data),
            patch("app.services.genderize_verifier._load_cache", return_value=mock_cache),
        ):
            stats, discrepancies = verificar_y_comparar("dummy.xlsx")

        # Ana: cache hit, Excel=M, cache=female=F → discrepancia
        # Pedro: cache miss, skipped
        # Hijo de Luis: forced male, Excel=M → OK
        # Hija de Laura: forced female, Excel=F → OK
        assert len(discrepancies) == 1
        assert discrepancies[0].numero_factura == "FAC-020"
        assert discrepancies[0].sexo_excel == "M"
        assert discrepancies[0].sexo_api == "F"
        # Stats: 4 unique, 1 cache hit (ana), 1 miss (pedro), 2 forced
        assert stats.api_calls_necesarias == 1  # solo pedro necesita API
        assert stats.cache_hits == 1
