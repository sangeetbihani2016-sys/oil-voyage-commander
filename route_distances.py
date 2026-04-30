from itertools import permutations
from math import asin, cos, radians, sin, sqrt


PORTS = {
    "Ras Tanura": {"country": "Saudi Arabia", "lat": 26.65, "lon": 50.16, "role": "Load"},
    "Ningbo": {"country": "China", "lat": 29.87, "lon": 121.55, "role": "Discharge"},
    "Singapore": {"country": "Singapore", "lat": 1.26, "lon": 103.84, "role": "Bunker / Transit"},
    "Fujairah": {"country": "United Arab Emirates", "lat": 25.13, "lon": 56.36, "role": "Bunker / Storage"},
    "Jebel Ali": {"country": "United Arab Emirates", "lat": 25.01, "lon": 55.06, "role": "Hub"},
    "Jamnagar": {"country": "India", "lat": 22.47, "lon": 69.72, "role": "Refinery"},
    "Rotterdam": {"country": "Netherlands", "lat": 51.95, "lon": 4.14, "role": "Discharge / Storage"},
    "Houston": {"country": "United States", "lat": 29.73, "lon": -95.26, "role": "Load / Discharge"},
    "Corpus Christi": {"country": "United States", "lat": 27.81, "lon": -97.40, "role": "Load"},
    "Sikka": {"country": "India", "lat": 22.43, "lon": 69.83, "role": "Load / Discharge"},
    "Qingdao": {"country": "China", "lat": 36.07, "lon": 120.32, "role": "Discharge"},
    "Ulsan": {"country": "South Korea", "lat": 35.50, "lon": 129.38, "role": "Refinery"},
}


CHOKEPOINTS = {
    "Hormuz": {"lat": 26.56, "lon": 56.25},
    "Malacca": {"lat": 1.43, "lon": 103.10},
    "Suez": {"lat": 30.58, "lon": 32.32},
    "Gibraltar": {"lat": 36.14, "lon": -5.35},
    "Panama": {"lat": 9.08, "lon": -79.68},
}


def haversine_nm(a, b):
    lat1, lon1 = radians(a["lat"]), radians(a["lon"])
    lat2, lon2 = radians(b["lat"]), radians(b["lon"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3440.065 * 2 * asin(sqrt(h))


def route_waypoints(origin, destination):
    origin_port = PORTS[origin]
    destination_port = PORTS[destination]
    points = [origin_port]

    if origin_port["lon"] > 40 and destination_port["lon"] > 90:
        points.extend([CHOKEPOINTS["Hormuz"], CHOKEPOINTS["Malacca"]])
    elif origin_port["lon"] > 40 and destination_port["lon"] < 15:
        points.extend([CHOKEPOINTS["Hormuz"], CHOKEPOINTS["Suez"], CHOKEPOINTS["Gibraltar"]])
    elif origin_port["lon"] < -50 and destination_port["lon"] > 40:
        points.extend([CHOKEPOINTS["Gibraltar"], CHOKEPOINTS["Suez"], CHOKEPOINTS["Hormuz"]])
    elif origin_port["lon"] < -50 and destination_port["lon"] > 90:
        points.extend([CHOKEPOINTS["Panama"], CHOKEPOINTS["Malacca"]])
    elif origin_port["lon"] < 15 and destination_port["lon"] > 90:
        points.extend([CHOKEPOINTS["Gibraltar"], CHOKEPOINTS["Suez"], CHOKEPOINTS["Hormuz"], CHOKEPOINTS["Malacca"]])

    points.append(destination_port)
    return points


def estimate_distance_nm(origin, destination):
    if origin == destination:
        return 0

    points = route_waypoints(origin, destination)
    distance = sum(haversine_nm(a, b) for a, b in zip(points, points[1:]))

    # Port-to-pilot-station deviation, traffic separation schemes, and coastline avoidance.
    if distance < 1500:
        multiplier = 1.14
    elif distance < 5000:
        multiplier = 1.10
    else:
        multiplier = 1.14

    return round(distance * multiplier)


def all_route_distances():
    return {
        f"{origin}__{destination}": {
            "origin": origin,
            "destination": destination,
            "distanceNm": estimate_distance_nm(origin, destination),
        }
        for origin, destination in permutations(PORTS.keys(), 2)
    }
