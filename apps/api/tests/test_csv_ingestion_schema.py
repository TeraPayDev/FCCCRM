from app.services.csv_schema import infer_csv_schema


def test_infer_csv_schema_detects_weather_fields() -> None:
    fields, row_count = infer_csv_schema(
        b"Temperature,Humidity,Wind_Speed,Cloud_Cover,Pressure,Rain\n"
        b"28.5,80,12.4,45.5,1012.4,rain\n"
        b"29.1,78,10.0,30.0,1011.8,no rain\n"
    )

    assert row_count == 2
    assert [(field["name"], field["data_type"]) for field in fields] == [
        ("Temperature", "number"),
        ("Humidity", "integer"),
        ("Wind_Speed", "number"),
        ("Cloud_Cover", "number"),
        ("Pressure", "number"),
        ("Rain", "string"),
    ]
    assert all(field["is_required"] is True for field in fields)
