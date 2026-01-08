# HomeSolar Add-on Repository

Home Assistant add-on repository for solar ephemeris tools.

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Installation

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the three dots menu (⋮) in the top right → **Repositories**
4. Add this repository URL:
   ```
   https://github.com/pehadavid/home-solar
   ```
5. Close the dialog and refresh the page
6. Find **HomeSolar - Solar Ephemeris** in the add-on list
7. Click on it and then click **Install**

## Add-ons

This repository contains the following add-on:

### [HomeSolar - Solar Ephemeris](./homesolar)

Complete solar ephemeris based on NOAA algorithm. Shows sunrise/sunset, civil/nautical/astronomical twilights, day duration and annual charts.

**Features:**
- 🌅 Precise sunrise/sunset calculation
- 🌆 Civil, nautical & astronomical twilights
- ⏱️ Day length tracking with daily comparisons
- 📊 Annual visualization of day length
- 🔔 Home Assistant events when phases are reached
- 📡 HA sensors for all solar times
- 🌍 Interactive map for location configuration
- 🔄 Auto-refresh every 5 minutes
- 🌍 Multi-language support (auto-detects from HA)

[View detailed documentation →](./homesolar/README.md)

## Support

If you encounter any issues, please [open an issue](https://github.com/pehadavid/home-solar/issues) on GitHub.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
