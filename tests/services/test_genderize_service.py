"""Tests for genderize_service — load_cache null→undefined, override_gender, predict_genders."""
import json
from unittest.mock import patch

from app.services.genderize_service import _load_cache, override_gender, predict_genders


# ── _load_cache: null → "undefined" ─────────────────────────────────────

class TestLoadCacheNullMapping:
    """Tests for _load_cache mapping null→"undefined"."""

    def test_null_gender_mapped_to_undefined(self):
        """GIVEN cache with null gender, WHEN _load_cache, THEN returns 'undefined'."""
        mock_data = json.dumps({"juan": {"gender": None, "probability": 0.99}})
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result["juan"]["gender"] == "undefined"

    def test_existing_values_preserved(self):
        """GIVEN cache with 'female'/'male', WHEN _load_cache, THEN unchanged."""
        mock_data = json.dumps({
            "ana": {"gender": "female", "probability": 0.95},
            "pablo": {"gender": "male", "probability": 0.99},
        })
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result["ana"]["gender"] == "female"
        assert result["pablo"]["gender"] == "male"

    def test_mixed_cache_preserves_and_maps(self):
        """GIVEN cache with null + valid mixed, WHEN _load_cache, THEN mixed handled correctly."""
        mock_data = json.dumps({
            "juan": {"gender": None},
            "ana": {"gender": "female"},
            "pedro": {"gender": None},
        })
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result["juan"]["gender"] == "undefined"
        assert result["ana"]["gender"] == "female"
        assert result["pedro"]["gender"] == "undefined"

    def test_empty_cache_returns_empty_dict(self):
        """GIVEN empty cache, WHEN _load_cache, THEN returns empty dict."""
        mock_data = "{}"
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result == {}

    def test_lastname_value_preserved(self):
        """GIVEN cache with 'lastname', WHEN _load_cache, THEN preserved."""
        mock_data = json.dumps({"jose": {"gender": "lastname", "probability": 0.0}})
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result["jose"]["gender"] == "lastname"

    def test_undefined_value_preserved(self):
        """GIVEN cache with 'undefined', WHEN _load_cache, THEN preserved."""
        mock_data = json.dumps({"test": {"gender": "undefined", "probability": 0.0}})
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = mock_data
            mock_file.parent.mkdir.return_value = None
            result = _load_cache()
        assert result["test"]["gender"] == "undefined"


# ── predict_genders: local-only (no API) ────────────────────────────────

class TestPredictGendersLocalOnly:
    """Tests for predict_genders operating cache-only (no API calls)."""

    def test_cache_hit_returns_gender_result(self):
        """GIVEN cache with entry, WHEN predict_genders, THEN returns GenderResult from cache."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {"juan": {"gender": "male", "probability": 0.99, "count": 100}}
            results = predict_genders(["juan"])
        assert len(results) == 1
        assert results[0].name == "juan"
        assert results[0].gender == "male"
        assert results[0].probability == 0.99
        assert results[0].count == 100

    def test_cache_miss_returns_empty(self):
        """GIVEN empty cache, WHEN predict_genders, THEN empty list."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {}
            results = predict_genders(["juan"])
        assert results == []

    def test_hijo_de_classified_locally(self):
        """GIVEN 'Hijo de' name not in cache, WHEN predict_genders, THEN classified via _classify."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {}
            results = predict_genders(["hijo de juan"])
        assert len(results) == 1
        assert results[0].name == "hijo de juan"
        assert results[0].gender == "male"

    def test_hija_de_classified_locally(self):
        """GIVEN 'Hija de' name not in cache, WHEN predict_genders, THEN classified via _classify."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {}
            results = predict_genders(["hija de maria"])
        assert len(results) == 1
        assert results[0].name == "hija de maria"
        assert results[0].gender == "female"

    def test_mixed_cache_hits_misses_and_hijo(self):
        """GIVEN mix of cached, uncached, and Hijo de names, THEN only cache hits + Hijo/Hija returned."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {"ana": {"gender": "female", "probability": 0.95, "count": 50}}
            results = predict_genders(["ana", "pedro", "hijo de carlos"])
        assert len(results) == 2
        result_dict = {r.name: r.gender for r in results}
        assert result_dict["ana"] == "female"
        assert result_dict["hijo de carlos"] == "male"
        assert "pedro" not in result_dict

    def test_empty_names_returns_empty_list(self):
        """GIVEN empty names list, WHEN predict_genders, THEN returns []."""
        results = predict_genders([])
        assert results == []

    def test_no_auto_u_on_cache_miss(self):
        """GIVEN name not in cache, WHEN predict_genders, THEN no 'U' or any value assigned."""
        with patch("app.services.genderize_service._load_cache") as mock_load:
            mock_load.return_value = {}
            results = predict_genders(["pedro"])
        assert results == []


# ── override_gender: accept 4 values ────────────────────────────────────

class TestOverrideGender:
    """Tests for override_gender accepting 4 values."""

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_short_f_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'F', THEN stores 'female'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "F")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "female"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_short_m_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'M', THEN stores 'male'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "M")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "male"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_short_l_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'L', THEN stores 'lastname'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "L")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "lastname"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_short_u_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'U', THEN stores 'undefined'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "U")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "undefined"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_long_female_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'female', THEN stores 'female'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "female")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "female"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_long_lastname_accepts(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'lastname', THEN stores 'lastname'."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        result = override_gender("juan", "lastname")
        assert result is True
        saved = mock_save.call_args[0][0]
        assert saved["juan"]["gender"] == "lastname"

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_invalid_value_raises_error(self, mock_save, mock_load):
        """GIVEN cache entry, WHEN override_gender with 'X', THEN raises ValueError."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        import pytest
        with pytest.raises(ValueError, match="genero invalido"):
            override_gender("juan", "X")

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_nonexistent_name_returns_false(self, mock_save, mock_load):
        """GIVEN no cache entry, WHEN override_gender, THEN returns False."""
        mock_load.return_value = {}
        result = override_gender("nonexistent", "M")
        assert result is False

    @patch("app.services.genderize_service._load_cache")
    @patch("app.services.genderize_service._save_cache")
    def test_cache_not_saved_on_invalid(self, mock_save, mock_load):
        """GIVEN invalid value, WHEN override_gender, THEN _save_cache NOT called."""
        mock_load.return_value = {"juan": {"gender": "undefined"}}
        import pytest
        with pytest.raises(ValueError):
            override_gender("juan", "X")
        mock_save.assert_not_called()
