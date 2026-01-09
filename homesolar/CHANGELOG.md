# Changelog

## [1.2.7.3]

### Fixed

- **Longitude normalization**: Clicking on wrapped map no longer shows validation error; longitude values outside -180/180 are now automatically normalized

## [1.2.7]

### Fixed

- **GPS Timezone**: Solar times now use the timezone of the GPS coordinates, not the system timezone
- Uses GeoNames API with fallback to longitude-based estimation (no compiled dependencies)

## [1.2.0]

### Added

- **Elevation support**: Automatic elevation retrieval from Open-Elevation API (NASA SRTM data)
- Horizon depression correction for more accurate sunrise/sunset times at altitude
- New `/api/elevation` endpoint to query elevation for any coordinates
- Elevation sensor in Home Assistant (`sensor.homesolar_elevation`)
- Elevation stored in configuration and passed to all calculations

### Changed
- Solar calculations now account for observer elevation (horizon depression formula)
- Location configuration now includes elevation (auto-fetched or manual override)
- All API responses now include elevation data

### Technical
- Modified `SolarCalculator._get_solar_altitude()` to apply horizon depression correction
- Added `elevation` parameter to `CompleteSolarModel` and `CompleteSolarInfo`
- Integrated Open-Elevation API call on location save

## [1.1.0] 
- Add HA Sensors 

## [1.0.5] 

### Added
- GitHub Copilot instructions for project consistency
- .gitignore for local development

## [1.0.4] 

### Fixed
- Minor bug fixes and improvements

## [1.0.3] 

### Added
- Language selection in add-on configuration (auto, en, fr)
- Translation files for configuration options
- Manual language override option in settings

### Changed
- Replaced auto_detect_language boolean with language dropdown
- Improved language detection logic with manual override support

### Fixed
- Fixed bashio::info.language command not found error
- Improved s6-overlay v3 compatibility

## [1.0.0] 

### Added
- Initial release of HomeSolar
- Solar calculator based on NOAA algorithm
- Sunrise/sunset times
- Civil, nautical, and astronomical twilights
- Day duration with daily comparison
- Annual duration chart
- Day/night progress bar
- Home Assistant ingress integration
- Custom Lovelace card
- REST API endpoints
- Multi-language support (English & French)
- Auto-detect language from Home Assistant
- Multi-architecture Docker support (amd64, aarch64, armhf, armv7, i386)
