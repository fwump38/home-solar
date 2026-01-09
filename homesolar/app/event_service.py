"""
HomeSolar Event Service
Monitors solar phases and fires events to Home Assistant
"""

import os
import json
import threading
import time
import logging
import requests
import pytz
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SolarPhase(Enum):
    """Solar phases that trigger events"""
    ASTRONOMICAL_DAWN = "astronomical_dawn"
    NAUTICAL_DAWN = "nautical_dawn"
    CIVIL_DAWN = "civil_dawn"
    SUNRISE = "sunrise"
    SOLAR_NOON = "solar_noon"
    SUNSET = "sunset"
    CIVIL_DUSK = "civil_dusk"
    NAUTICAL_DUSK = "nautical_dusk"
    ASTRONOMICAL_DUSK = "astronomical_dusk"


@dataclass
class ScheduledEvent:
    """A scheduled solar event"""
    phase: SolarPhase
    time: datetime
    fired: bool = False


class HomeAssistantEventService:
    """
    Service to fire events to Home Assistant when solar phases are reached.
    Uses the Home Assistant Supervisor API available to add-ons.
    """
    
    EVENT_TYPE = "homesolar_phase"
    SENSOR_PREFIX = "sensor.homesolar_"
    
    def __init__(self):
        self.supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
        self.supervisor_url = "http://supervisor/core/api"
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.scheduled_events: Dict[SolarPhase, ScheduledEvent] = {}
        self.last_update_date: Optional[datetime] = None
        self._solar_info = None
        self.timezone_str: str = "UTC"  # Will be updated when schedule_events is called
        
        # Check if we're running in Home Assistant
        self.ha_available = bool(self.supervisor_token)
        if not self.ha_available:
            logger.warning("SUPERVISOR_TOKEN not found - running outside Home Assistant")
    
    def _get_headers(self) -> dict:
        """Get headers for Home Assistant API calls"""
        return {
            "Authorization": f"Bearer {self.supervisor_token}",
            "Content-Type": "application/json"
        }
    
    def _get_now(self) -> datetime:
        """Get current time in the configured timezone (naive datetime for comparison)"""
        tz = pytz.timezone(self.timezone_str)
        return datetime.now(tz).replace(tzinfo=None)
    
    def fire_event(self, phase: SolarPhase, event_data: dict = None) -> bool:
        """
        Fire an event to Home Assistant.
        
        Event type: homesolar_phase
        Event data includes:
        - phase: The solar phase name
        - time: The time of the event
        - latitude/longitude: Location
        """
        if not self.ha_available:
            logger.info(f"[SIMULATION] Would fire event: {phase.value}")
            return False
        
        try:
            data = {
                "phase": phase.value,
                "timestamp": self._get_now().isoformat(),
                **(event_data or {})
            }
            
            response = requests.post(
                f"{self.supervisor_url}/events/{self.EVENT_TYPE}",
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Event fired: {self.EVENT_TYPE} - {phase.value}")
                return True
            else:
                logger.error(f"Failed to fire event: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error firing event: {e}")
            return False
    
    def update_sensor(self, sensor_name: str, state: Any, attributes: dict = None) -> bool:
        """
        Update a sensor state in Home Assistant.
        Creates the sensor if it doesn't exist.
        """
        if not self.ha_available:
            logger.debug(f"[SIMULATION] Would update sensor: {sensor_name} = {state}")
            return False
        
        try:
            entity_id = f"{self.SENSOR_PREFIX}{sensor_name}"
            data = {
                "state": str(state),
                "attributes": {
                    "friendly_name": f"HomeSolar {sensor_name.replace('_', ' ').title()}",
                    "icon": self._get_icon_for_sensor(sensor_name),
                    **(attributes or {})
                }
            }
            
            response = requests.post(
                f"{self.supervisor_url}/states/{entity_id}",
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Error updating sensor {sensor_name}: {e}")
            return False
    
    def _get_icon_for_sensor(self, sensor_name: str) -> str:
        """Get appropriate MDI icon for sensor"""
        icons = {
            "sunrise": "mdi:weather-sunset-up",
            "sunset": "mdi:weather-sunset-down",
            "solar_noon": "mdi:weather-sunny",
            "day_length": "mdi:timer-outline",
            "current_phase": "mdi:sun-clock",
            "next_event": "mdi:clock-outline",
            "astronomical_dawn": "mdi:weather-night",
            "nautical_dawn": "mdi:sail-boat",
            "civil_dawn": "mdi:city",
            "civil_dusk": "mdi:city",
            "nautical_dusk": "mdi:sail-boat",
            "astronomical_dusk": "mdi:weather-night",
            "elevation": "mdi:elevation-rise",
        }
        return icons.get(sensor_name, "mdi:sun-wireless")
    
    def schedule_events(self, solar_info, timezone_str: str = "UTC") -> None:
        """
        Schedule events for all solar phases based on calculated times.
        Called when solar data is updated.
        
        Args:
            solar_info: Solar information with times
            timezone_str: Timezone string for the GPS location (e.g., "Asia/Tokyo")
        """
        self._solar_info = solar_info
        self.timezone_str = timezone_str  # Update timezone for _get_now()
        today = self._get_now().date()
        
        # Clear old events if day changed
        if self.last_update_date != today:
            self.scheduled_events.clear()
            self.last_update_date = today
        
        # Schedule each phase
        phase_times = [
            (SolarPhase.ASTRONOMICAL_DAWN, solar_info.astronomical_dawn),
            (SolarPhase.NAUTICAL_DAWN, solar_info.nautical_dawn),
            (SolarPhase.CIVIL_DAWN, solar_info.civil_dawn),
            (SolarPhase.SUNRISE, solar_info.sunrise),
            (SolarPhase.SOLAR_NOON, solar_info.solar_noon),
            (SolarPhase.SUNSET, solar_info.sunset),
            (SolarPhase.CIVIL_DUSK, solar_info.civil_dusk),
            (SolarPhase.NAUTICAL_DUSK, solar_info.nautical_dusk),
            (SolarPhase.ASTRONOMICAL_DUSK, solar_info.astronomical_dusk),
        ]
        
        now = self._get_now()
        
        for phase, event_time in phase_times:
            if event_time:
                # Check if already passed today
                already_passed = event_time <= now
                
                self.scheduled_events[phase] = ScheduledEvent(
                    phase=phase,
                    time=event_time,
                    fired=already_passed  # Mark as fired if already passed
                )
        
        # Update all sensors
        self._update_all_sensors(solar_info)
        
        logger.info(f"Scheduled {len(self.scheduled_events)} solar events for today")
    
    def _update_all_sensors(self, solar_info) -> None:
        """Update all Home Assistant sensors with current solar data"""
        
        # Location sensors (including elevation)
        if hasattr(solar_info, 'elevation'):
            self.update_sensor("elevation", f"{solar_info.elevation:.0f}", {
                "unit_of_measurement": "m",
                "elevation_meters": solar_info.elevation,
                "latitude": getattr(solar_info, 'latitude', None),
                "longitude": getattr(solar_info, 'longitude', None)
            })
        
        # Time sensors
        if solar_info.sunrise:
            self.update_sensor("sunrise", solar_info.sunrise.strftime("%H:%M"), {
                "timestamp": solar_info.sunrise.isoformat()
            })
        
        if solar_info.sunset:
            self.update_sensor("sunset", solar_info.sunset.strftime("%H:%M"), {
                "timestamp": solar_info.sunset.isoformat()
            })
        
        if solar_info.solar_noon:
            self.update_sensor("solar_noon", solar_info.solar_noon.strftime("%H:%M"), {
                "timestamp": solar_info.solar_noon.isoformat()
            })
        
        # Day length
        if solar_info.day_length:
            hours = int(solar_info.day_length.total_seconds() // 3600)
            minutes = int((solar_info.day_length.total_seconds() % 3600) // 60)
            self.update_sensor("day_length", f"{hours}h {minutes}m", {
                "total_minutes": int(solar_info.day_length.total_seconds() / 60),
                "total_seconds": int(solar_info.day_length.total_seconds())
            })
        
        # Twilight times
        twilights = [
            ("astronomical_dawn", solar_info.astronomical_dawn),
            ("nautical_dawn", solar_info.nautical_dawn),
            ("civil_dawn", solar_info.civil_dawn),
            ("civil_dusk", solar_info.civil_dusk),
            ("nautical_dusk", solar_info.nautical_dusk),
            ("astronomical_dusk", solar_info.astronomical_dusk),
        ]
        
        for name, time_value in twilights:
            if time_value:
                self.update_sensor(name, time_value.strftime("%H:%M"), {
                    "timestamp": time_value.isoformat()
                })
        
        # Current phase
        current_phase = self._get_current_phase(solar_info)
        self.update_sensor("current_phase", current_phase, {
            "phase_key": current_phase.lower().replace(" ", "_")
        })
        
        # Next event
        next_event = self._get_next_event()
        if next_event:
            self.update_sensor("next_event", next_event.phase.value, {
                "time": next_event.time.strftime("%H:%M"),
                "timestamp": next_event.time.isoformat(),
                "minutes_until": int((next_event.time - self._get_now()).total_seconds() / 60)
            })
    
    def _get_current_phase(self, solar_info) -> str:
        """Determine current solar phase"""
        now = self._get_now()
        
        if solar_info.is_polar_night:
            return "Polar Night"
        if solar_info.is_polar_day:
            return "Polar Day"
        
        if not solar_info.sunrise or not solar_info.sunset:
            return "Unknown"
        
        if solar_info.sunrise <= now <= solar_info.sunset:
            return "Day"
        
        # Evening twilights
        if solar_info.sunset and solar_info.civil_dusk:
            if solar_info.sunset < now <= solar_info.civil_dusk:
                return "Civil Twilight"
        if solar_info.civil_dusk and solar_info.nautical_dusk:
            if solar_info.civil_dusk < now <= solar_info.nautical_dusk:
                return "Nautical Twilight"
        if solar_info.nautical_dusk and solar_info.astronomical_dusk:
            if solar_info.nautical_dusk < now <= solar_info.astronomical_dusk:
                return "Astronomical Twilight"
        
        # Morning twilights
        if solar_info.astronomical_dawn and solar_info.nautical_dawn:
            if solar_info.astronomical_dawn <= now < solar_info.nautical_dawn:
                return "Astronomical Dawn"
        if solar_info.nautical_dawn and solar_info.civil_dawn:
            if solar_info.nautical_dawn <= now < solar_info.civil_dawn:
                return "Nautical Dawn"
        if solar_info.civil_dawn and solar_info.sunrise:
            if solar_info.civil_dawn <= now < solar_info.sunrise:
                return "Civil Dawn"
        
        return "Night"
    
    def _get_next_event(self) -> Optional[ScheduledEvent]:
        """Get the next unfired event"""
        now = self._get_now()
        next_event = None
        
        for event in self.scheduled_events.values():
            if not event.fired and event.time > now:
                if next_event is None or event.time < next_event.time:
                    next_event = event
        
        return next_event
    
    def check_and_fire_events(self) -> None:
        """Check if any scheduled events should be fired"""
        now = self._get_now()
        
        for phase, event in self.scheduled_events.items():
            if not event.fired and event.time <= now:
                # Time to fire this event!
                event_data = {
                    "latitude": self._solar_info.latitude if self._solar_info else None,
                    "longitude": self._solar_info.longitude if self._solar_info else None,
                    "scheduled_time": event.time.isoformat(),
                }
                
                self.fire_event(phase, event_data)
                event.fired = True
                
                # Update next_event sensor
                next_event = self._get_next_event()
                if next_event:
                    self.update_sensor("next_event", next_event.phase.value, {
                        "time": next_event.time.strftime("%H:%M"),
                        "timestamp": next_event.time.isoformat()
                    })
                
                # Update current phase sensor
                if self._solar_info:
                    current_phase = self._get_current_phase(self._solar_info)
                    self.update_sensor("current_phase", current_phase)
    
    def _monitor_loop(self) -> None:
        """Background thread that monitors for events"""
        logger.info("Event monitor started")
        
        while self.running:
            try:
                self.check_and_fire_events()
            except Exception as e:
                logger.error(f"Error in event monitor: {e}")
            
            # Check every 30 seconds
            time.sleep(30)
        
        logger.info("Event monitor stopped")
    
    def start(self) -> None:
        """Start the event monitoring service"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("HomeSolar Event Service started")
    
    def stop(self) -> None:
        """Stop the event monitoring service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("HomeSolar Event Service stopped")


# Global instance
event_service = HomeAssistantEventService()
