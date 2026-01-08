"""
HomeSolar - Flask Application for Home Assistant Add-on
Complete solar ephemeris based on NOAA algorithm
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import pytz

from solar_calculator import (
    SolarCalculator, 
    CompleteSolarModel, 
    CompleteSolarInfo,
    TwilightType
)
from event_service import event_service

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration file path (persistent storage)
CONFIG_FILE = Path(os.environ.get('CONFIG_PATH', '/share/homesolar/config.json'))

# Default configuration from environment variables
DEFAULT_LATITUDE = float(os.environ.get('LATITUDE', 48.8566))
DEFAULT_LONGITUDE = float(os.environ.get('LONGITUDE', 2.3522))
TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Paris')
HA_LANGUAGE = os.environ.get('HA_LANGUAGE', 'en')
CONFIG_LANGUAGE = os.environ.get('LANGUAGE', 'auto')
INGRESS_ENTRY = os.environ.get('INGRESS_ENTRY', '')


def load_config():
    """Load configuration from persistent storage"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f"Error loading config: {e}")
    return None


def get_elevation(latitude: float, longitude: float) -> float:
    """
    Get elevation from Open-Elevation API.
    Returns elevation in meters, or 0 if unavailable.
    """
    try:
        import urllib.request
        import urllib.parse
        
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={latitude},{longitude}"
        req = urllib.request.Request(url, headers={'User-Agent': 'HomeSolar/1.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if data and 'results' in data and len(data['results']) > 0:
            elevation = data['results'][0].get('elevation', 0)
            app.logger.info(f"Elevation retrieved: {elevation}m for ({latitude}, {longitude})")
            return float(elevation) if elevation is not None else 0.0
    except Exception as e:
        app.logger.warning(f"Could not get elevation from Open-Elevation API: {e}")
    
    return 0.0


def save_config(config):
    """Save configuration to persistent storage"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        app.logger.error(f"Error saving config: {e}")
        return False


def get_location():
    """Get current location and elevation (from config file or defaults)"""
    config = load_config()
    if config:
        return (
            config.get('latitude', DEFAULT_LATITUDE),
            config.get('longitude', DEFAULT_LONGITUDE),
            config.get('elevation', 0.0)
        )
    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE, 0.0


# Current location (loaded at startup, can be updated via API)
LATITUDE, LONGITUDE, ELEVATION = get_location()

# Supported languages
SUPPORTED_LANGUAGES = ['en', 'fr']

def get_language():
    """Get the current language (from config or auto-detect from HA)"""
    # If language is explicitly set (not auto), use it
    if CONFIG_LANGUAGE != 'auto':
        return CONFIG_LANGUAGE if CONFIG_LANGUAGE in SUPPORTED_LANGUAGES else 'en'
    
    # Auto-detect from Home Assistant
    if HA_LANGUAGE in SUPPORTED_LANGUAGES:
        return HA_LANGUAGE
    
    # Default to English
    return 'en'


def get_timezone_offset(timezone_str: str) -> int:
    """Calculate current timezone offset"""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        offset = now.utcoffset()
        return int(offset.total_seconds() // 3600) if offset else 0
    except:
        return 0


def format_duration(duration: timedelta) -> str:
    """Format duration in HH:MM:SS format"""
    total_seconds = int(abs(duration.total_seconds()))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_current_phase(info: CompleteSolarInfo) -> dict:
    """Determine current solar phase"""
    now = datetime.now()
    
    if info.is_polar_night:
        return {"phase": "polar_night", "icon": "🌑"}
    if info.is_polar_day:
        return {"phase": "polar_day", "icon": "☀️"}
    
    if not info.sunrise or not info.sunset:
        return {"phase": "unknown", "icon": "❓"}
    
    # During the day
    if info.sunrise <= now <= info.sunset:
        return {"phase": "day", "icon": "☀️"}
    
    # Civil twilight evening
    if info.sunset and info.civil_dusk and info.sunset < now <= info.civil_dusk:
        return {"phase": "civil_twilight", "icon": "🌆"}
    
    # Nautical twilight evening
    if info.civil_dusk and info.nautical_dusk and info.civil_dusk < now <= info.nautical_dusk:
        return {"phase": "nautical_twilight", "icon": "⚓"}
    
    # Astronomical twilight evening
    if info.nautical_dusk and info.astronomical_dusk and info.nautical_dusk < now <= info.astronomical_dusk:
        return {"phase": "astronomical_twilight", "icon": "🌌"}
    
    # Astronomical dawn
    if info.astronomical_dawn and info.nautical_dawn and info.astronomical_dawn <= now < info.nautical_dawn:
        return {"phase": "astronomical_dawn", "icon": "🌌"}
    
    # Nautical dawn
    if info.nautical_dawn and info.civil_dawn and info.nautical_dawn <= now < info.civil_dawn:
        return {"phase": "nautical_dawn", "icon": "⚓"}
    
    # Civil dawn
    if info.civil_dawn and info.sunrise and info.civil_dawn <= now < info.sunrise:
        return {"phase": "civil_dawn", "icon": "🌅"}
    
    return {"phase": "night", "icon": "🌙"}


def calculate_progress(info: CompleteSolarInfo) -> dict:
    """Calculate day or night progress"""
    now = datetime.now()
    
    if not info.sunrise or not info.sunset:
        return {"progress": 0, "elapsed": "-", "remaining": "-", "is_day": False}
    
    is_day = info.sunrise <= now <= info.sunset
    
    if is_day:
        total = (info.sunset - info.sunrise).total_seconds()
        elapsed = (now - info.sunrise).total_seconds()
        progress = (elapsed / total * 100) if total > 0 else 0
        remaining = info.sunset - now
        
        return {
            "progress": min(100, max(0, progress)),
            "elapsed": format_duration(timedelta(seconds=elapsed)),
            "remaining": format_duration(remaining),
            "is_day": True
        }
    else:
        # Night - calculate from sunset to next sunrise
        if now > info.sunset:
            # After sunset
            next_sunrise = info.sunrise + timedelta(days=1)
            total = (next_sunrise - info.sunset).total_seconds()
            elapsed = (now - info.sunset).total_seconds()
        else:
            # Before sunrise
            prev_sunset = info.sunset - timedelta(days=1)
            total = (info.sunrise - prev_sunset).total_seconds()
            elapsed = (now - prev_sunset).total_seconds()
        
        progress = (elapsed / total * 100) if total > 0 else 0
        remaining = info.sunrise - now if now < info.sunrise else (info.sunrise + timedelta(days=1)) - now
        
        return {
            "progress": min(100, max(0, progress)),
            "elapsed": format_duration(timedelta(seconds=elapsed)),
            "remaining": format_duration(remaining),
            "is_day": False
        }


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', 
                          ingress_entry=INGRESS_ENTRY,
                          latitude=LATITUDE,
                          longitude=LONGITUDE,
                          language=get_language())


@app.route('/api/solar')
def get_solar_data():
    """API to retrieve solar data"""
    lat = request.args.get('lat', LATITUDE, type=float)
    lon = request.args.get('lon', LONGITUDE, type=float)
    elev = request.args.get('elevation', ELEVATION, type=float)
    
    tz_offset = get_timezone_offset(TIMEZONE)
    
    # Calculate solar information with elevation correction
    model = CompleteSolarModel(lat, lon, tz_offset, elevation=elev)
    info = model.current_solar_info
    
    # Add location info for event service
    info.latitude = lat
    info.longitude = lon
    info.elevation = elev
    
    # Schedule events for Home Assistant
    event_service.schedule_events(info)
    
    # Calculate progress
    progress = calculate_progress(info)
    
    # Current phase
    phase = get_current_phase(info)
    
    # Difference from yesterday
    diff = model.get_diff()
    diff_sign = model.get_sign()
    
    response = {
        "date": datetime.now().strftime("%A %d %B %Y"),
        "latitude": lat,
        "longitude": lon,
        "elevation": elev,
        "timezone": TIMEZONE,
        "sunrise": info.sunrise.strftime("%H:%M") if info.sunrise else None,
        "sunset": info.sunset.strftime("%H:%M") if info.sunset else None,
        "sunrise_datetime": info.sunrise.isoformat() if info.sunrise else None,
        "sunset_datetime": info.sunset.isoformat() if info.sunset else None,
        "solar_noon": info.solar_noon.strftime("%H:%M") if info.solar_noon else None,
        "civil_dawn": info.civil_dawn.strftime("%H:%M") if info.civil_dawn else None,
        "civil_dusk": info.civil_dusk.strftime("%H:%M") if info.civil_dusk else None,
        "nautical_dawn": info.nautical_dawn.strftime("%H:%M") if info.nautical_dawn else None,
        "nautical_dusk": info.nautical_dusk.strftime("%H:%M") if info.nautical_dusk else None,
        "astronomical_dawn": info.astronomical_dawn.strftime("%H:%M") if info.astronomical_dawn else None,
        "astronomical_dusk": info.astronomical_dusk.strftime("%H:%M") if info.astronomical_dusk else None,
        "day_length": info.get_human_readable_duration(),
        "is_polar_night": info.is_polar_night,
        "is_polar_day": info.is_polar_day,
        "diff": format_duration(diff),
        "diff_sign": diff_sign,
        "diff_positive": diff.total_seconds() >= 0,
        "progress": progress,
        "phase": phase,
        "current_time": datetime.now().strftime("%H:%M:%S"),
        "language": get_language()
    }
    
    return jsonify(response)


@app.route('/api/chart')
def get_chart_data():
    """API for annual chart data"""
    lat = request.args.get('lat', LATITUDE, type=float)
    lon = request.args.get('lon', LONGITUDE, type=float)
    elev = request.args.get('elevation', ELEVATION, type=float)
    
    tz_offset = get_timezone_offset(TIMEZONE)
    model = CompleteSolarModel(lat, lon, tz_offset, elevation=elev)
    
    return jsonify(model.get_chart_data())


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current location configuration"""
    lat, lon, elev = get_location()
    config = load_config() or {}
    return jsonify({
        "latitude": lat,
        "longitude": lon,
        "elevation": elev,
        "timezone": TIMEZONE,
        "location_name": config.get('location_name', ''),
        "is_configured": CONFIG_FILE.exists()
    })


@app.route('/api/config', methods=['POST'])
def set_config():
    """Save location configuration from map selection"""
    global LATITUDE, LONGITUDE, ELEVATION
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    lat = data.get('latitude')
    lon = data.get('longitude')
    location_name = data.get('location_name', '')
    # Allow manual elevation override, otherwise fetch automatically
    manual_elevation = data.get('elevation')
    
    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude required"}), 400
    
    try:
        lat = float(lat)
        lon = float(lon)
        
        if not (-90 <= lat <= 90):
            return jsonify({"error": "Latitude must be between -90 and 90"}), 400
        if not (-180 <= lon <= 180):
            return jsonify({"error": "Longitude must be between -180 and 180"}), 400
        
        # Get elevation: use manual value if provided, otherwise fetch from API
        if manual_elevation is not None:
            elev = float(manual_elevation)
        else:
            elev = get_elevation(lat, lon)
        
        config = {
            "latitude": lat,
            "longitude": lon,
            "elevation": elev,
            "location_name": location_name,
            "updated_at": datetime.now().isoformat()
        }
        
        if save_config(config):
            # Update global variables
            LATITUDE = lat
            LONGITUDE = lon
            ELEVATION = elev
            return jsonify({
                "success": True,
                "latitude": lat,
                "longitude": lon,
                "elevation": elev,
                "location_name": location_name
            })
        else:
            return jsonify({"error": "Failed to save configuration"}), 500
            
    except ValueError as e:
        return jsonify({"error": f"Invalid coordinates: {e}"}), 400


@app.route('/api/search')
def search_location():
    """Search for a location using Nominatim (OpenStreetMap)"""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        import urllib.request
        import urllib.parse
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=5"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'HomeSolar/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
        results = []
        for item in data:
            results.append({
                "name": item.get('display_name', ''),
                "latitude": float(item.get('lat', 0)),
                "longitude": float(item.get('lon', 0))
            })
        
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify([])


@app.route('/api/elevation')
def get_elevation_api():
    """
    API to get elevation for given coordinates.
    Uses Open-Elevation API (SRTM data from NASA).
    """
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon parameters required"}), 400
    
    elevation = get_elevation(lat, lon)
    
    return jsonify({
        "latitude": lat,
        "longitude": lon,
        "elevation": elevation,
        "unit": "meters",
        "source": "Open-Elevation API (SRTM)"
    })


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "version": "1.0.0", 
        "addon": "homesolar",
        "language": get_language(),
        "events_enabled": event_service.ha_available
    })


@app.route('/api/events')
def get_events():
    """API to get scheduled events status"""
    events = []
    for phase, event in event_service.scheduled_events.items():
        events.append({
            "phase": phase.value,
            "time": event.time.strftime("%H:%M:%S") if event.time else None,
            "timestamp": event.time.isoformat() if event.time else None,
            "fired": event.fired
        })
    
    # Sort by time
    events.sort(key=lambda x: x["timestamp"] or "")
    
    return jsonify({
        "events": events,
        "ha_available": event_service.ha_available,
        "running": event_service.running
    })


# Start event service when module loads
def initialize_app():
    """Initialize the application and start services"""
    # Start the event monitoring service
    event_service.start()
    
    # Load initial solar data to schedule events
    lat, lon, elev = get_location()
    tz_offset = get_timezone_offset(TIMEZONE)
    model = CompleteSolarModel(lat, lon, tz_offset, elevation=elev)
    info = model.current_solar_info
    info.latitude = lat
    info.longitude = lon
    info.elevation = elev
    event_service.schedule_events(info)
    
    app.logger.info(f"HomeSolar initialized at ({lat}, {lon}, {elev}m) - Events service running: {event_service.ha_available}")


# Initialize on first request
with app.app_context():
    initialize_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099, debug=True)
