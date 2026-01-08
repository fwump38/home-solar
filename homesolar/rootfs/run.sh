#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Home Assistant Add-on: HomeSolar
# Runs the HomeSolar application
# ==============================================================================

declare latitude
declare longitude
declare timezone
declare auto_detect_language
declare ha_language

# Read configuration
latitude=$(bashio::config 'latitude')
longitude=$(bashio::config 'longitude')
timezone=$(bashio::config 'timezone')
auto_detect_language=$(bashio::config 'auto_detect_language')

# Get ingress settings
export INGRESS_ENTRY=$(bashio::addon.ingress_entry)

# Get Home Assistant language (with fallback to 'en')
ha_language="en"
if bashio::fs.file_exists '/data/options.json'; then
    ha_language=$(bashio::jq "/data/options.json" '.language // "en"' 2>/dev/null || echo "en")
fi

# Try to get language from Home Assistant API
if bashio::var.has_value "$(bashio::api.supervisor GET /core/info false .language 2>/dev/null)"; then
    ha_language=$(bashio::api.supervisor GET /core/info false .language)
fi

# Export variables for the app
export LATITUDE="${latitude}"
export LONGITUDE="${longitude}"
export TIMEZONE="${timezone}"
export AUTO_DETECT_LANGUAGE="${auto_detect_language}"
export HA_LANGUAGE="${ha_language}"

bashio::log.info "Starting HomeSolar - Solar Ephemeris..."
bashio::log.info "Position: ${latitude}, ${longitude}"
bashio::log.info "Timezone: ${timezone}"
bashio::log.info "Language: ${ha_language}"

cd /app || bashio::exit.nok "Cannot change to /app directory"
exec gunicorn --bind 0.0.0.0:8099 --workers 1 --threads 2 app:app
