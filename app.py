from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)

# Get Azure Maps subscription key from environment variable
AZURE_MAPS_KEY = os.environ.get('AZURE_MAPS_KEY')
if not AZURE_MAPS_KEY:
    raise RuntimeError('AZURE_MAPS_KEY environment variable not set!')

@app.route('/')
def index():
    return render_template(
        'index.html',
        azure_maps_key=AZURE_MAPS_KEY
    )

@app.route('/route', methods=['POST'])
def get_route():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    efficiency = data.get('efficiency')
    vehicle_type = data.get('vehicle_type', 'combustion')  # 'combustion' or 'electric'
    debug = data.get('debug', False)
    traffic = data.get('traffic', False)
    try:
        efficiency = float(efficiency)
        if efficiency <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'Consumo/Eficiência inválido.'}), 400

    # Geocode addresses to coordinates
    def geocode(address):
        url = f"https://atlas.microsoft.com/search/address/json?api-version=1.0&subscription-key={AZURE_MAPS_KEY}&query={address}"
        resp = requests.get(url)
        if resp.status_code == 200:
            results = resp.json().get('results')
            if results:
                pos = results[0]['position']
                return f"{pos['lat']},{pos['lon']}"
        return None

    origin_coords = geocode(origin)
    destination_coords = geocode(destination)
    if not origin_coords or not destination_coords:
        return jsonify({'error': 'Could not geocode addresses.'}), 400

    traffic_param = '&traffic=true' if traffic else ''
    route_url = f"https://atlas.microsoft.com/route/directions/json?api-version=1.0&subscription-key={AZURE_MAPS_KEY}&query={origin_coords}:{destination_coords}{traffic_param}"
    route_resp = requests.get(route_url)
    if route_resp.status_code == 200:
        route_data = route_resp.json()
        summary = route_data['routes'][0]['summary']
        distance_km = summary['lengthInMeters'] / 1000
        travel_time_min = summary.get('travelTimeInSecondsWithTraffic', summary['travelTimeInSeconds']) / 60
        # Calculate based on vehicle type
        fuel_liters = None
        energy_kwh = None
        if vehicle_type in ['combustion', 'combustão']:
            fuel_liters = distance_km / efficiency
        elif vehicle_type in ['electric', 'elétrico']:
            energy_kwh = distance_km / efficiency
        legs = route_data['routes'][0]['legs'][0]['points']
        coordinates = [[pt['latitude'], pt['longitude']] for pt in legs]
        response = {
            'distance_km': round(distance_km, 2),
            'fuel_liters': round(fuel_liters, 2) if fuel_liters is not None else None,
            'energy_kwh': round(energy_kwh, 2) if energy_kwh is not None else None,
            'travel_time_min': round(travel_time_min, 1),
            'coordinates': coordinates
        }
        if debug:
            response['raw_api'] = route_data
        return jsonify(response)
    else:
        return jsonify({'error': 'Could not get route.'}), 400

@app.route('/incidents', methods=['POST'])
def get_incidents():
    data = request.json
    min_lat = data.get('min_lat')
    min_lng = data.get('min_lng')
    max_lat = data.get('max_lat')
    max_lng = data.get('max_lng')
    print(f"[DEBUG] Received bounding box: min_lat={min_lat}, min_lng={min_lng}, max_lat={max_lat}, max_lng={max_lng}")
    # Validate all values are present and are valid numbers
    try:
        min_lat = float(min_lat)
        min_lng = float(min_lng)
        max_lat = float(max_lat)
        max_lng = float(max_lng)
        for v in (min_lat, min_lng, max_lat, max_lng):
            if not isinstance(v, float) or v != v or v == float('inf') or v == float('-inf'):
                raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'Bounding box required and must be valid numbers.'}), 400
    # Use the correct API endpoint and parameters as per latest docs
    bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"
    url = (
        f"https://atlas.microsoft.com/traffic/incident?api-version=2025-01-01"
        f"&subscription-key={AZURE_MAPS_KEY}"
        f"&bbox={bbox}"
    )
    resp = requests.get(url)

    if resp.status_code == 200:
        data = resp.json()
        # Only return relevant info to frontend
        incidents = []
        for feature in data.get('features', []):
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})
            if geometry.get('type') == 'Point':
                incidents.append({
                    'coordinates': geometry.get('coordinates'),
                    'title': properties.get('title', 'Incidente'),
                    'description': properties.get('description', ''),
                    'incidentType': properties.get('incidentType', ''),
                    'severity': properties.get('severity', ''),
                    'delay': properties.get('delay', ''),
                    'startTime': properties.get('startTime', ''),
                    'endTime': properties.get('endTime', ''),
                    'isTrafficJam': properties.get('isTrafficJam', False),
                    'isRoadClosed': properties.get('isRoadClosed', False)
                })
        print(f"[DEBUG] Incidents returned: {len(incidents)}")
        return jsonify({'incidents': incidents})
    else:
        print(f"[DEBUG] Could not get incidents. Response: {resp.text}")
        return jsonify({'error': 'Could not get incidents.'}), 400

if __name__ == '__main__':
    app.run(debug=True)
