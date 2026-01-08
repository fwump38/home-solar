# HomeSolar - Solar Ephemeris for Home Assistant

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

Complete solar ephemeris Home Assistant add-on based on NOAA (National Oceanic and Atmospheric Administration) algorithm.

![Screenshot](docs/screenshot.png)

## Features

- 🌅 **Sunrise and sunset** - Precise times calculated for your location
- 🌆 **Civil twilight** - When the sun is between 0° and 6° below horizon
- ⚓ **Nautical twilight** - When the sun is between 6° and 12° below horizon  
- 🌌 **Astronomical twilight** - When the sun is between 12° and 18° below horizon
- ⏱️ **Day length** - With comparison to previous day
- 📊 **Annual chart** - Visualization of day length over the year
- 🌙 **Day/night progress** - Real-time progress bar
- � **Home Assistant Events** - Fires events when solar phases are reached
- 📡 **HA Sensors** - Creates sensors for all solar times
- �🔄 **Auto-refresh** - Data updated every 5 minutes
- 🌍 **Multi-language** - Auto-detects language from Home Assistant (English & French supported)
- 📍 **Interactive map** - Configure your location directly from the interface using Leaflet

## Installation

### Via Add-on Store

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the three dots menu (top right) → **Repositories**
4. Add this repository: `https://github.com/pehadavid/home-solar`
5. Search for "HomeSolar" and install

### Manual Installation

1. Copy the `home-solar` folder to `/addons/` in your Home Assistant installation
2. Restart Home Assistant
3. Go to **Settings** → **Add-ons** → **HomeSolar**
4. Click **Install**

## Configuration

The add-on can be configured in two ways:

### Option 1: Interactive Map (Recommended)

1. Open the HomeSolar panel from the sidebar
2. Click the **⚙️ Settings** button
3. Search for a city or click directly on the map
4. Click **Save Location**

The location is saved persistently and will be used even after restart.

### Option 2: YAML Configuration

```yaml
latitude: 48.8566      # Your latitude (default: Paris)
longitude: 2.3522      # Your longitude
timezone: "Europe/Paris"  # Your timezone
auto_detect_language: true  # Auto-detect language from HA
```

> 💡 **Tip**: The interactive map configuration takes priority over YAML settings.

## Access the Interface

Once installed and started:

1. A new **HomeSolar** item appears in the Home Assistant sidebar
2. Click it to access the complete interface

## Custom Lovelace Card

You can also add a card to your dashboard:

### Card Installation

1. Copy `lovelace/homesolar-card.js` to `/config/www/`
2. Add the resource in **Settings** → **Dashboards** → **Resources**:
   ```yaml
   url: /local/homesolar-card.js
   type: module
   ```

### Usage

Add a manual card with this configuration:

```yaml
type: custom:homesolar-card
addon_slug: homesolar
show_twilights: true
```

### Card Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `addon_slug` | string | `homesolar` | Add-on slug |
| `show_twilights` | boolean | `true` | Show detailed twilights |

## REST API

The add-on exposes a REST API accessible via ingress:

### Current Solar Data

```
GET /api/solar?lat={latitude}&lon={longitude}
```

Response:
```json
{
  "date": "Thursday, January 8, 2026",
  "sunrise": "08:43",
  "sunset": "17:12",
  "solar_noon": "12:57",
  "civil_dawn": "08:08",
  "civil_dusk": "17:47",
  "nautical_dawn": "07:29",
  "nautical_dusk": "18:26",
  "astronomical_dawn": "06:51",
  "astronomical_dusk": "19:04",
  "day_length": "8h 29min",
  "diff": "1m 23s",
  "diff_sign": "+",
  "progress": {
    "progress": 45.2,
    "elapsed": "3h 52m",
    "remaining": "4h 37m",
    "is_day": true
  },
  "phase": {
    "phase": "day",
    "icon": "☀️"
  },
  "language": "en"
}
```

### Annual Chart Data

```
GET /api/chart?lat={latitude}&lon={longitude}
```

### Events Status

```
GET /api/events
```

Response:
```json
{
  "events": [
    {"phase": "astronomical_dawn", "time": "06:51:23", "fired": true},
    {"phase": "nautical_dawn", "time": "07:29:45", "fired": true},
    {"phase": "civil_dawn", "time": "08:08:12", "fired": false},
    {"phase": "sunrise", "time": "08:43:00", "fired": false},
    {"phase": "solar_noon", "time": "12:57:30", "fired": false},
    {"phase": "sunset", "time": "17:12:00", "fired": false},
    {"phase": "civil_dusk", "time": "17:47:00", "fired": false},
    {"phase": "nautical_dusk", "time": "18:26:00", "fired": false},
    {"phase": "astronomical_dusk", "time": "19:04:00", "fired": false}
  ],
  "ha_available": true,
  "running": true
}
```

## Home Assistant Integration

### Events

HomeSolar fires Home Assistant events when solar phases are reached. You can use these events in automations.

#### Event Type: `homesolar_phase`

Fired for each solar phase (dawn, sunrise, noon, sunset, dusk).

**Event data:**
```yaml
phase: sunrise  # Phase name
timestamp: "2026-01-08T08:43:00"
latitude: 48.8566
longitude: 2.3522
scheduled_time: "2026-01-08T08:43:00"
```

**Available phases:**
| Phase | Description |
|-------|-------------|
| `astronomical_dawn` | Start of astronomical twilight (sun 18° below horizon) |
| `nautical_dawn` | Start of nautical twilight (sun 12° below horizon) |
| `civil_dawn` | Start of civil twilight (sun 6° below horizon) |
| `sunrise` | Sunrise (sun's upper edge at horizon) |
| `solar_noon` | Solar noon (sun at highest point) |
| `sunset` | Sunset (sun's upper edge at horizon) |
| `civil_dusk` | End of civil twilight |
| `nautical_dusk` | End of nautical twilight |
| `astronomical_dusk` | End of astronomical twilight |

### Sensors

HomeSolar creates sensors in Home Assistant:

| Sensor | Description |
|--------|-------------|
| `sensor.homesolar_sunrise` | Today's sunrise time |
| `sensor.homesolar_sunset` | Today's sunset time |
| `sensor.homesolar_solar_noon` | Solar noon time |
| `sensor.homesolar_day_length` | Day duration |
| `sensor.homesolar_current_phase` | Current solar phase |
| `sensor.homesolar_next_event` | Next solar event |
| `sensor.homesolar_civil_dawn` | Civil dawn time |
| `sensor.homesolar_civil_dusk` | Civil dusk time |
| `sensor.homesolar_nautical_dawn` | Nautical dawn time |
| `sensor.homesolar_nautical_dusk` | Nautical dusk time |
| `sensor.homesolar_astronomical_dawn` | Astronomical dawn time |
| `sensor.homesolar_astronomical_dusk` | Astronomical dusk time |

### Automation Examples

#### Turn on lights at civil dusk

```yaml
automation:
  - alias: "Turn on outdoor lights at civil dusk"
    trigger:
      - platform: event
        event_type: homesolar_phase
        event_data:
          phase: civil_dusk
    action:
      - service: light.turn_on
        target:
          entity_id: light.outdoor_lights
```

#### Morning announcement at sunrise

```yaml
automation:
  - alias: "Good morning announcement"
    trigger:
      - platform: event
        event_type: homesolar_phase
        event_data:
          phase: sunrise
    action:
      - service: tts.speak
        data:
          message: "Good morning! The sun has risen."
        target:
          entity_id: tts.google_en_com
```

#### Close blinds at nautical dusk

```yaml
automation:
  - alias: "Close blinds at nautical dusk"
    trigger:
      - platform: event
        event_type: homesolar_phase
        event_data:
          phase: nautical_dusk
    action:
      - service: cover.close_cover
        target:
          entity_id: cover.all_blinds
```

## Calculation Algorithm

Solar calculations are based on:

- **NOAA Algorithm** (National Oceanic and Atmospheric Administration)
- **Wikipedia Sunrise Equation**
- Takes into account:
  - Atmospheric refraction (-0.833°)
  - Earth's axial tilt (23.4397°)
  - Equation of time
  - Sun's mean anomaly

### Twilight Types

| Type | Solar Angle | Description |
|------|-------------|-------------|
| Sunrise/Sunset | -0.833° | Sun's upper edge at horizon |
| Civil | -6° | Outdoor activities without artificial light |
| Nautical | -12° | Maritime horizon visible + stars |
| Astronomical | -18° | Completely dark sky |

## Troubleshooting

### Add-on won't start

1. Check logs in **Settings** → **Add-ons** → **HomeSolar** → **Log**
2. Ensure port 8099 is not used by another service

### Times appear incorrect

1. Verify your timezone is correctly configured
2. Check your GPS coordinates (latitude/longitude)

### Lovelace card not displaying

1. Clear your browser cache
2. Verify the JS file is in `/config/www/`
3. Check that the resource is correctly added

## Contributing

Contributions are welcome! Feel free to:

- 🐛 Report bugs
- 💡 Suggest improvements
- 🔧 Submit pull requests

## License

 See [LICENSE](LICENSE) for details.

## Credits

- Based on NOAA algorithm
- Inspired by the original MamaSoleil project
- Icons by [Emoji](https://emojipedia.org/)

---

**Made with ❤️ for the Home Assistant community**
