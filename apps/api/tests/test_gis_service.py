from app.db.seed_gis import SAMPLE_CODE, SAMPLE_LAYER


def test_sample_gis_identifiers_are_explicitly_synthetic() -> None:
    assert "SAMPLE" in SAMPLE_CODE
    assert "Sample" in SAMPLE_LAYER
