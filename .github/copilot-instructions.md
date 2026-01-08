# GitHub Copilot Instructions for HomeSolar Project

## Project Overview
HomeSolar is a Home Assistant add-on that provides complete solar ephemeris calculations based on the NOAA algorithm. It displays sunrise/sunset times, twilight information, day duration, and annual charts.

## Technology Stack
- **Backend**: Python 3.11 with Flask
- **Frontend**: HTML/CSS/JavaScript with Leaflet for maps
- **Container**: Docker with Alpine Linux base
- **Init System**: s6-overlay v3
- **Home Assistant Integration**: Via ingress and REST API

## Key Features
- Solar ephemeris calculations (sunrise, sunset, twilights)
- Interactive OpenStreetMap for location selection
- Multi-language support (English, French)
- Real-time day/night progress tracking
- Annual solar duration visualization
- Home Assistant native integration

## Architecture

### Directory Structure
```
home-solar/
├── homesolar/              # Add-on folder
│   ├── app/               # Flask application
│   │   ├── app.py         # Main Flask app
│   │   ├── solar_calculator.py
│   │   ├── static/        # CSS, JavaScript, assets
│   │   └── templates/     # HTML templates
│   ├── config.yaml        # Add-on configuration
│   ├── Dockerfile         # Container definition
│   ├── build.yaml         # Build configuration
│   ├── rootfs/            # Root filesystem
│   │   ├── etc/s6-overlay/ # s6-overlay v3 services
│   │   └── run.sh         # Startup script
│   ├── translations/      # i18n files (en.yaml, fr.yaml)
│   ├── lovelace/          # Custom Lovelace card
│   └── requirements.txt   # Python dependencies
├── repository.json        # Repository metadata
├── repository.yaml        # Repository configuration
└── README.md              # Documentation
```

## Important Guidelines

### Configuration Management
- **config.yaml**: Defines add-on configuration, options, and schema
- Options include: latitude, longitude, timezone, language
- Language options: "auto" (detect from HA), "en", "fr"
- Always update version when making changes

### Docker & s6-overlay
- Use s6-overlay v3 (Alpine Linux base image)
- Set `init: false` in config.yaml when using s6-overlay
- Services defined in `rootfs/etc/s6-overlay/s6-rc.d/`
- Scripts use bashio library for Home Assistant integration

### Scripts & Startup
- Main startup: `rootfs/etc/s6-overlay/s6-rc.d/homesolar/run`
- Alternative: `rootfs/run.sh` (for compatibility)
- Scripts must use `#!/usr/bin/with-contenv bashio` shebang
- Config values read with `bashio::config 'option_name'`

### Language & Translation
- Supported languages: English (en), French (fr)
- Translation files: `homesolar/translations/{en,fr}.yaml`
- Format: YAML with configuration, network sections
- Language selection via `LANGUAGE` environment variable

### Flask Application
- Main app: `homesolar/app/app.py`
- Solar calculations: `homesolar/app/solar_calculator.py`
- Config stored persistently in `/share/homesolar/config.json`
- Ingress support for Home Assistant native panel
- REST API endpoints for location and solar data

### Version & Changelog
- Version in config.yaml should be semantic (e.g., 1.0.4)
- Update CHANGELOG.md with each release
- Format: [VERSION] - DATE with Added/Changed/Fixed sections

## Code Quality Standards
- Use bashio functions for scripts (don't spawn subshells)
- Error handling with `bashio::exit.nok "message"`
- Proper variable declaration and quoting in bash
- Python code should follow PEP 8
- Comments in English for clarity

## Testing & Deployment
- Always increment version before push
- Commit message format: "Description" or "Type: Description"
- Push to main branch via git
- Home Assistant Rebuild for version detection
- Check logs for s6-overlay and Flask startup

## Common Tasks

### Adding a Feature
1. Modify relevant code files
2. Update translations if needed
3. Increment version in config.yaml
4. Update CHANGELOG.md
5. Commit and push

### Fixing Bugs
1. Identify issue in logs
2. Apply fix to code
3. Test with Home Assistant Rebuild
4. Increment patch version
5. Commit and push

### Updating Language Support
1. Add language code to config.yaml schema
2. Create translation file in translations/
3. Update get_language() function if needed
4. Test language selection in HA settings

## Environment Variables
- `LATITUDE`: Location latitude
- `LONGITUDE`: Location longitude
- `TIMEZONE`: Timezone string (e.g., "Europe/Paris")
- `LANGUAGE`: Language selection (auto, en, fr)
- `HA_LANGUAGE`: Detected Home Assistant language
- `INGRESS_ENTRY`: Ingress path from Home Assistant

## Useful Links
- [Home Assistant Add-ons Documentation](https://developers.home-assistant.io/docs/add-ons)
- [s6-overlay Documentation](https://github.com/just-containers/s6-overlay)
- [bashio Library](https://github.com/hassio-addons/bashio)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Quick Debug Commands
```bash
# Check logs in Home Assistant
ha addons log homesolar

# Rebuild add-on
ha addons rebuild homesolar

# View configuration
ha config show

# Check Home Assistant API
curl http://supervisor/core/api/
```

## Notes for Copilot
- When suggesting changes, ensure s6-overlay v3 compatibility
- Always include error handling in shell scripts
- Maintain backward compatibility where possible
- Keep language files synchronized with code strings
- Update version and changelog with every change
- Test suggestions in Home Assistant environment
