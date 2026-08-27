from datetime import datetime, timezone

def to_utc(epoch):
    # OpenSky timestamps are Unix epoch seconds, UTC.
    # Some (like time_position) can be null — guard for that.
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)

def clean_callsign(raw):
    # Callsigns are padded to 8 chars with trailing spaces; can also be null.
    if raw is None:
        return None
    return raw.strip()

def parse_state(state, poll_time):
    return {
        "icao24":         state[0],
        "callsign":       clean_callsign(state[1]),
        "origin_country": state[2],
        "time_position":  to_utc(state[3]),
        "last_contact":   to_utc(state[4]),
        "longitude":      state[5],
        "latitude":       state[6],
        "baro_altitude":  state[7],
        "on_ground":      state[8],
        "velocity":       state[9],
        "true_track":     state[10],
        "vertical_rate":  state[11],
        "geo_altitude":   state[13],
        "squawk":         state[14],
        "position_source":state[16],
        "poll_time":      poll_time,
    }

def parse_response(response):
    flight_data = []
    poll_time = to_utc(response["time"])
    states = response["states"]
    if states is None: # catches any empty data points and prevents from crashing
        return []
    for state in states:
        aircraft_data_pt = parse_state(state, poll_time)
        flight_data.append(aircraft_data_pt)
    return flight_data