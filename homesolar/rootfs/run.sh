#!/usr/bin/with-contenv bashio

# Read configuration
CONFIG_PATH=/data/options.json
export LATITUDE=$(bashio::config 'latitude')
export LONGITUDE=$(bashio::config 'longitude')
export TIMEZONE=$(bashio::config 'timezone')
export AUTO_DETECT_LANGUAGE=$(bashio::config 'auto_detect_language')

# Get ingress settings
export INGRESS_ENTRY=$(bashio::addon.ingress_entry)

# Get Home Assistant language
export HA_LANGUAGE=$(bashio::info.language)

bashio::log.info "Starting HomeSolar - Solar Ephemeris..."
bashio::log.info "Position: ${LATITUDE}, ${LONGITUDE}"
bashio::log.info "Timezone: ${TIMEZONE}"
bashio::log.info "Language: ${HA_LANGUAGE}"

cd /app
exec gunicorn --bind 0.0.0.0:8099 --workers 1 --threads 2 app:app
