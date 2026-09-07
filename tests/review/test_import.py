"""Test that importing easyscielo.review works without optional extras."""

import easyscielo.review


def test_import_review() -> None:
    """Verify easyscielo.review can be imported without extras."""
    assert hasattr(easyscielo.review, "__all__")
    assert isinstance(easyscielo.review.__all__, list)
    assert "SystematicReview" in easyscielo.review.__all__
