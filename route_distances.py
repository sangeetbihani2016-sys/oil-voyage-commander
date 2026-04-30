from itertools import permutations
from math import asin, cos, radians, sin, sqrt


PORTS = {
    "Ras Tanura": {"country": "Saudi Arabia", "lat": 26.65, "lon": 50.16, "role": "Load"},
    "Juaymah": {"country": "Saudi Arabia", "lat": 26.93, "lon": 50.03, "role": "Load"},
    "Yanbu": {"country": "Saudi Arabia", "lat": 24.09, "lon": 38.06, "role": "Load / Refinery"},
    "Basrah Oil Terminal": {"country": "Iraq", "lat": 29.68, "lon": 48.82, "role": "Load"},
    "Mina Al Ahmadi": {"country": "Kuwait", "lat": 29.08, "lon": 48.15, "role": "Load / Refinery"},
    "Kharg Island": {"country": "Iran", "lat": 29.24, "lon": 50.31, "role": "Load"},
    "Fujairah": {"country": "United Arab Emirates", "lat": 25.13, "lon": 56.36, "role": "Bunker / Storage"},
    "Jebel Ali": {"country": "United Arab Emirates", "lat": 25.01, "lon": 55.06, "role": "Hub"},
    "Sikka": {"country": "India", "lat": 22.43, "lon": 69.83, "role": "Load / Discharge"},
    "Jamnagar": {"country": "India", "lat": 22.47, "lon": 69.72, "role": "Refinery"},
    "Mumbai": {"country": "India", "lat": 18.94, "lon": 72.84, "role": "Discharge"},
    "Paradip": {"country": "India", "lat": 20.27, "lon": 86.70, "role": "Discharge / Refinery"},
    "Singapore": {"country": "Singapore", "lat": 1.26, "lon": 103.84, "role": "Bunker / Transit"},
    "Port Klang": {"country": "Malaysia", "lat": 3.00, "lon": 101.39, "role": "Storage / Transit"},
    "Ningbo": {"country": "China", "lat": 29.87, "lon": 121.55, "role": "Discharge"},
    "Zhoushan": {"country": "China", "lat": 29.99, "lon": 122.21, "role": "Storage / Discharge"},
    "Qingdao": {"country": "China", "lat": 36.07, "lon": 120.32, "role": "Discharge"},
    "Dalian": {"country": "China", "lat": 38.91, "lon": 121.65, "role": "Discharge / Refinery"},
    "Ulsan": {"country": "South Korea", "lat": 35.50, "lon": 129.38, "role": "Refinery"},
    "Yeosu": {"country": "South Korea", "lat": 34.74, "lon": 127.74, "role": "Refinery"},
    "Chiba": {"country": "Japan", "lat": 35.56, "lon": 140.10, "role": "Refinery"},
    "Rotterdam": {"country": "Netherlands", "lat": 51.95, "lon": 4.14, "role": "Discharge / Storage"},
    "Antwerp": {"country": "Belgium", "lat": 51.26, "lon": 4.40, "role": "Discharge / Storage"},
    "Trieste": {"country": "Italy", "lat": 45.65, "lon": 13.77, "role": "Discharge"},
    "Augusta": {"country": "Italy", "lat": 37.23, "lon": 15.22, "role": "Refinery"},
    "Fos-sur-Mer": {"country": "France", "lat": 43.43, "lon": 4.90, "role": "Discharge / Refinery"},
    "Ceyhan": {"country": "Turkey", "lat": 36.86, "lon": 35.93, "role": "Load"},
    "Novorossiysk": {"country": "Russia", "lat": 44.72, "lon": 37.78, "role": "Load"},
    "Primorsk": {"country": "Russia", "lat": 60.35, "lon": 28.61, "role": "Load"},
    "Es Sider": {"country": "Libya", "lat": 30.63, "lon": 18.35, "role": "Load"},
    "Zawia": {"country": "Libya", "lat": 32.79, "lon": 12.71, "role": "Load / Refinery"},
    "Skikda": {"country": "Algeria", "lat": 36.88, "lon": 6.91, "role": "Load / Refinery"},
    "Bonny": {"country": "Nigeria", "lat": 4.43, "lon": 7.17, "role": "Load"},
    "Forcados": {"country": "Nigeria", "lat": 5.35, "lon": 5.22, "role": "Load"},
    "Luanda": {"country": "Angola", "lat": -8.78, "lon": 13.24, "role": "Load"},
    "Saldanha Bay": {"country": "South Africa", "lat": -33.03, "lon": 17.96, "role": "Storage / Transit"},
    "Houston": {"country": "United States", "lat": 29.73, "lon": -95.26, "role": "Load / Discharge"},
    "Corpus Christi": {"country": "United States", "lat": 27.81, "lon": -97.40, "role": "Load"},
    "LOOP": {"country": "United States", "lat": 28.89, "lon": -90.03, "role": "Load / Discharge"},
    "Covenas": {"country": "Colombia", "lat": 9.40, "lon": -75.69, "role": "Load"},
    "Jose Terminal": {"country": "Venezuela", "lat": 10.10, "lon": -64.88, "role": "Load"},
    "Sao Sebastiao": {"country": "Brazil", "lat": -23.80, "lon": -45.39, "role": "Load / Discharge"},
}


CHOKEPOINTS = {
    "Hormuz": {"lat": 26.56, "lon": 56.25},
    "Malacca": {"lat": 1.43, "lon": 103.10},
    "Suez": {"lat": 30.58, "lon": 32.32},
    "Gibraltar": {"lat": 36.14, "lon": -5.35},
    "Panama": {"lat": 9.08, "lon": -79.68},
    "Cape of Good Hope": {"lat": -34.35, "lon": 18.47},
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
    elif origin_port["lon"] < -30 and destination_port["lon"] > 90:
        points.extend([CHOKEPOINTS["Cape of Good Hope"], CHOKEPOINTS["Malacca"]])
    elif origin_port["lon"] < 20 and destination_port["lon"] > 90 and origin_port["lat"] < 15:
        points.extend([CHOKEPOINTS["Cape of Good Hope"], CHOKEPOINTS["Malacca"]])
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
