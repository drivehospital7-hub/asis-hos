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


# ── list_cache: NFD search, gender filter, sort, pagination ─────────────

class TestListCache:
    """RED: list_cache helpers (PR1 T1.1)."""

    def test_nfd_search_accented_query_matches_plain_key(self):
        """GIVEN key 'angela' via Ángela, WHEN search='Ángela', THEN match via _normalize."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(search="Ángela")
        assert result["total"] == 1
        assert result["items"][0]["nombre_normalizado"] == "angela"

    def test_search_case_insensitive_substring(self):
        """GIVEN keys, WHEN search='ANG' case-insensitive, THEN substring match."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "angelica": {"gender": "female", "probability": 0.9, "count": 2},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(search="ang")
        assert result["total"] == 2

    def test_empty_search_returns_all(self):
        """GIVEN empty/None search, THEN all entries returned paginated."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(search=None)
        assert result["total"] == 2

    def test_no_results_empty_items(self):
        """GIVEN search='zzzznotfound', THEN items:[] total:0."""
        from app.services.genderize_service import list_cache

        fake_cache = {"angela": {"gender": "female", "probability": 0.99, "count": 10}}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(search="zzzznotfound")
        assert result["items"] == []
        assert result["total"] == 0

    def test_gender_filter_short_f(self):
        """GIVEN gender='F', THEN only female entries."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(gender="F")
        assert result["total"] == 1
        assert result["items"][0]["gender"] == "female"
        assert result["items"][0]["gender_short"] == "F"

    def test_gender_filter_long_lastname(self):
        """GIVEN gender='lastname', THEN only lastname entries (equiv L)."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "garcia": {"gender": "lastname", "probability": 0.5, "count": 1},
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(gender="lastname")
        assert result["total"] == 1
        assert result["items"][0]["gender"] == "lastname"

    def test_gender_all_no_filter(self):
        """GIVEN gender='All', THEN no filter."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(gender="All")
        assert result["total"] == 2

    def test_gender_invalid_raises(self):
        """GIVEN gender='X' invalid, THEN raises ValueError."""
        from app.services.genderize_service import list_cache

        fake_cache = {"angela": {"gender": "female", "probability": 0.99, "count": 10}}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            import pytest

            with pytest.raises(ValueError, match="genero invalido"):
                list_cache(gender="X")

    def test_alpha_sort_by_normalized_key(self):
        """GIVEN unsorted keys, THEN sorted by _normalize asc."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "zara": {"gender": "female", "probability": 0.9, "count": 1},
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "maria": {"gender": "female", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache()
        keys = [i["nombre_normalizado"] for i in result["items"]]
        assert keys == ["angela", "maria", "zara"]

    def test_pagination_defaults(self):
        """GIVEN 11k entries, WHEN no paging, THEN page 1 page_size 50 first 50 alpha."""
        from app.services.genderize_service import list_cache

        fake_cache = {f"name{i:04d}": {"gender": "female", "probability": 0.9, "count": 1} for i in range(100)}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache()
        assert result["page"] == 1
        assert result["page_size"] == 50
        assert len(result["items"]) == 50
        assert result["total"] == 100

    def test_pagination_page_out_of_range(self):
        """GIVEN page=9999 total=100, THEN items:[] total unchanged echoed page."""
        from app.services.genderize_service import list_cache

        fake_cache = {f"name{i}": {"gender": "female", "probability": 0.9, "count": 1} for i in range(5)}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(page=9999, page_size=50)
        assert result["items"] == []
        assert result["total"] == 5
        assert result["page"] == 9999

    def test_pagination_clamp_page_size(self):
        """GIVEN page_size=200 >100, THEN clamped to 100."""
        from app.services.genderize_service import list_cache

        fake_cache = {f"name{i}": {"gender": "female", "probability": 0.9, "count": 1} for i in range(150)}
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache(page_size=200)
        assert result["page_size"] == 100
        assert len(result["items"]) == 100

    def test_by_gender_counts_filtered_set(self):
        """GIVEN mixed genders, THEN by_gender correct on filtered set."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "maria": {"gender": "female", "probability": 0.95, "count": 5},
            "jose": {"gender": "male", "probability": 0.9, "count": 3},
            "garcia": {"gender": "lastname", "probability": 0.5, "count": 1},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            result = list_cache()
        # by_gender uses short codes F/M/L/U
        assert result["by_gender"]["F"] == 2
        assert result["by_gender"]["M"] == 1
        assert result["by_gender"]["L"] == 1

    def test_gender_filter_case_insensitive(self):
        """GIVEN gender='f' lowercase, THEN same as 'F'."""
        from app.services.genderize_service import list_cache

        fake_cache = {
            "angela": {"gender": "female", "probability": 0.99, "count": 10},
            "jose": {"gender": "male", "probability": 0.95, "count": 5},
        }
        with patch("app.services.genderize_service._load_cache", return_value=fake_cache):
            r1 = list_cache(gender="f")
            r2 = list_cache(gender="F")
        assert r1["total"] == r2["total"] == 1


# ── get_cache_alerts: raw scan ───────────────────────────────────────

class TestGetCacheAlerts:
    """RED: get_cache_alerts (PR1 T1.2)."""

    def test_bom_same_value_collision(self):
        """GIVEN raw '\\ufeffangela' and 'angela' same gender, THEN collision same_value true + cleaned_keys."""
        from app.services.genderize_service import get_cache_alerts
        import json as _json

        raw_dict = {
            "\ufeffangela": {"gender": "female", "probability": 0.99, "count": 1},
            "angela": {"gender": "female", "probability": 0.99, "count": 1},
        }
        raw_text = _json.dumps(raw_dict, ensure_ascii=False)
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = raw_text
            result = get_cache_alerts()
        assert result["total_collisions"] == 1
        coll = result["collisions"][0]
        assert coll["same_value"] is True
        assert "\ufeffangela" in coll["raw_keys"]
        assert "\ufeffangela" in result["cleaned_keys"]

    def test_nfd_different_value_collision(self):
        """GIVEN 'José'(female) and 'jose'(male), THEN collision different_value."""
        from app.services.genderize_service import get_cache_alerts
        import json as _json

        raw_dict = {
            "José": {"gender": "female", "probability": 0.9, "count": 1},
            "jose": {"gender": "male", "probability": 0.9, "count": 1},
        }
        raw_text = _json.dumps(raw_dict, ensure_ascii=False)
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = raw_text
            result = get_cache_alerts()
        assert result["total_collisions"] == 1
        assert result["collisions"][0]["same_value"] is False
        assert set(result["collisions"][0]["genders"]) == {"female", "male"}

    def test_invalid_genders_detected(self):
        """GIVEN entry gender='X', THEN invalid_genders contains it."""
        from app.services.genderize_service import get_cache_alerts
        import json as _json

        raw_dict = {"foo": {"gender": "X", "probability": 0.9, "count": 1}}
        raw_text = _json.dumps(raw_dict, ensure_ascii=False)
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = raw_text
            result = get_cache_alerts()
        assert any(i["key"] == "foo" and i["gender"] == "X" for i in result["invalid_genders"])

    def test_recovered_nulls_counted(self):
        """GIVEN entry gender None, THEN recovered_nulls >=1."""
        from app.services.genderize_service import get_cache_alerts
        import json as _json

        raw_dict = {"juan": {"gender": None, "probability": None, "count": None}}
        raw_text = _json.dumps(raw_dict, ensure_ascii=False)
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = raw_text
            result = get_cache_alerts()
        assert result["recovered_nulls"] == 1

    def test_missing_file_returns_empty(self):
        """GIVEN missing cache file, THEN empty collisions."""
        from app.services.genderize_service import get_cache_alerts

        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.side_effect = FileNotFoundError()
            result = get_cache_alerts()
        assert result["collisions"] == []
        assert result["total_collisions"] == 0
        assert result["cleaned_keys"] == []
        assert result["invalid_genders"] == []
        assert result["recovered_nulls"] == 0

    def test_zw_cleaned_keys(self):
        """GIVEN key with ZW char, THEN cleaned_keys includes raw."""
        from app.services.genderize_service import get_cache_alerts
        import json as _json

        raw_dict = {"angela\u200b": {"gender": "female", "probability": 0.9, "count": 1}}
        raw_text = _json.dumps(raw_dict, ensure_ascii=False)
        with patch("app.services.genderize_service.CACHE_FILE") as mock_file:
            mock_file.read_text.return_value = raw_text
            result = get_cache_alerts()
        assert "angela\u200b" in result["cleaned_keys"]
