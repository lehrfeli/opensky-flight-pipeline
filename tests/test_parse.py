import json
from datetime import datetime
from pipeline.parse import parse_response

def test_parse_response():
    # 1. Load the known input (as if using collect.py)
    with open("data/sample_response.json") as f:
        response = json.load(f)

    # run the parse_response function
    records = parse_response(response)

    assert len(records) == 9
    first_record = records[0]
    last_record = records[-1]
    assert first_record["icao24"] == "a3975b"
    assert first_record["origin_country"] == "United States"
    assert first_record["callsign"] == "SIS330"
    assert last_record["callsign"] =="EJA612"
    assert isinstance(first_record["time_position"], datetime)
    assert isinstance(first_record["last_contact"], datetime)
    assert isinstance(first_record["poll_time"], datetime)
    assert records[3]["squawk"] is None
    assert first_record["poll_time"] == last_record["poll_time"]