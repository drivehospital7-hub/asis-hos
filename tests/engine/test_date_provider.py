"""Unit tests for DateProvider — computes age and hours from invoice date fields."""

from __future__ import annotations

import pytest
from datetime import datetime


class TestDateProvider:
    """Tests for DateProvider (prefix='date') — edad and horas resolution."""

    def test_computes_valid_age(self):
        """Compute age from fecha_nacimiento and fecha_factura."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": "2010-05-15",
            "fec_factura": "2026-06-24",
        })
        result = provider.resolve("date.edad", ctx)
        assert result == 16  # 2026-06-24 - 2010-05-15 = 16 years

    def test_computes_age_birthday_not_reached(self):
        """Age when birthday hasn't occurred yet this year."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": "2010-12-25",
            "fec_factura": "2026-06-24",
        })
        result = provider.resolve("date.edad", ctx)
        assert result == 15  # Birthday Dec 25 hasn't happened yet

    def test_computes_hours_diff(self):
        """Compute hours difference between fec_factura and fecha_cierre."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_factura": "2026-06-24 08:00:00",
            "fecha_cierre": "2026-06-24 20:00:00",
        })
        result = provider.resolve("date.horas", ctx)
        assert result == 12

    def test_returns_none_for_invalid_date(self):
        """Returns None when dates can't be parsed."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": "not-a-date",
            "fec_factura": "garbage",
        })
        result = provider.resolve("date.edad", ctx)
        assert result is None

    def test_returns_none_for_missing_field(self):
        """Returns None when required fields are missing."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": "2010-05-15",
            # fec_factura is missing
        })
        result = provider.resolve("date.edad", ctx)
        assert result is None

    def test_handles_datetime_objects(self):
        """Works with datetime objects, not just strings."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": datetime(2010, 5, 15),
            "fec_factura": datetime(2026, 6, 24),
        })
        result = provider.resolve("date.edad", ctx)
        assert result == 16

    def test_edge_future_birth_date(self):
        """Future birth date returns negative age or None — handle gracefully."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={
            "fec_nacimiento": "2030-01-01",
            "fec_factura": "2026-06-24",
        })
        result = provider.resolve("date.edad", ctx)
        # Future birth date: age would be negative, return None as invalid
        assert result is None

    def test_unknown_date_path_returns_none(self):
        """Unrecognized date.* path returns None."""
        from app.services.engine.providers import DateProvider
        from app.services.engine.context import EvaluationContext

        provider = DateProvider()
        ctx = EvaluationContext(invoice_data={})
        result = provider.resolve("date.unknown", ctx)
        assert result is None

    def test_prefix_property(self):
        """Prefix is 'date'."""
        from app.services.engine.providers import DateProvider
        provider = DateProvider()
        assert provider.prefix == "date"
