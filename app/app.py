"""
HomeSolar - Flask Application for Home Assistant Add-on
Complete solar ephemeris based on NOAA algorithm
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import pytz

from solar_calculator import (
    SolarCalculator, 
    CompleteSolarModel, 
    CompleteSolarInfo,
    TwilightType
)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration from environment variables
LATITUDE = float(os.environ.get('LATITUDE', 48.8566))
LONGITUDE = float(os.environ.get('LONGITUDE', 2.3522))
TIMEZONE = os.environ.get('TIMEZONE', 'Europe/Paris')
HA_LANGUAGE = os.environ.get('HA_LANGUAGE', 'en')
AUTO_DETECT_LANGUAGE = os.environ.get('AUTO_DETECT_LANGUAGE', 'true').lower() == 'true'
INGRESS_ENTRY = os.environ.get('INGRESS_ENTRY', '')

# Supported languages
SUPPORTED_LANGUAGES = ['en', 'fr']

def get_language():
    """Get the current language (from HA or default to English)"""
    if AUTO_DETECT_LANGUAGE and HA_LANGUAGE in SUPPORTED_LANGUAGES:
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
    """Format duration in readable format"""
    total_seconds = abs(duration.total_seconds())
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m {seconds}s"


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
    
    tz_offset = get_timezone_offset(TIMEZONE)
    ate solar information
    model = CompleteSolarModel(lat, lon, tz_offset)
    info = model.current_solar_info
    
    # Calculate progress
    progress = calculate_progress(info)
    
    # Current phase
    phase = get_current_phase(info)
    
    # Difference from yesterday
    # Différence avec hier
    diff = model.get_diff()
    diff_sign = model.get_sign()
    
    response = {
        "date": datetime.now().strftime("%A %d %B %Y"),
        "latitude": lat,
        "longitude": lon,
        "timezone": TIMEZONE,
        "sunrise": info.sunrise.strftime("%H:%M") if info.sunrise else None,
        "sunset": info.sunset.strftime("%H:%M") if info.sunset else None,
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
        "phase": phase,,
        "language": get_language()
    }
    
    return jsonify(response)


@app.route('/api/chart')
def get_chart_data():
    """API for annual chart data
    """API pour les données du graphique annuel"""
    lat = request.args.get('lat', LATITUDE, type=float)
    lon = request.args.get('lon', LONGITUDE, type=float)
    
    tz_offset = get_timezone_offset(TIMEZONE)
    model = CompleteSolarModel(lat, lon, tz_offset)
    
    return jsonify(model.get_chart_data())


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "version": "1.0.0", 
        "addon": "homesolar",
        "language": get_language()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099, debug=True)
