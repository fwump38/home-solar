# Changelog

## [1.1.0] - 2026-01-08
- Add HA Sensors 

## [1.0.5] - 2026-01-08

### Added
- GitHub Copilot instructions for project consistency
- .gitignore for local development

## [1.0.4] - 2026-01-08

### Fixed
- Minor bug fixes and improvements

## [1.0.3] - 2026-01-08

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

## [1.0.0] - 2026-01-08

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
