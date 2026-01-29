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
    
    # Event type for progress events
    PROGRESS_EVENT_TYPE = "homesolar_progress"
    
    # Progress thresholds that trigger events (in percent)
    PROGRESS_THRESHOLDS = [10, 25, 50, 75, 90]
    
    def __init__(self):
        self.supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
        self.supervisor_url = "http://supervisor/core/api"
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.scheduled_events: Dict[SolarPhase, ScheduledEvent] = {}
        self.last_update_date: Optional[datetime] = None
        self._solar_info = None
        self.timezone_str: str = "UTC"  # Will be updated when schedule_events is called
        
        # Progress tracking
        self._last_progress_update: Optional[datetime] = None
        self._fired_day_thresholds: set = set()  # Track which day thresholds have been fired
        self._fired_night_thresholds: set = set()  # Track which night thresholds have been fired
        self._last_is_day: Optional[bool] = None  # Track day/night transitions
        
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
    
    def fire_progress_event(self, is_day: bool, progress: float, threshold: int, event_data: dict = None) -> bool:
        """
        Fire a progress event to Home Assistant.
        
        Event type: homesolar_progress
        Event data includes:
        - period: "day" or "night"
        - progress: Current progress percentage
        - threshold: The threshold that was crossed
        - elapsed: Time elapsed
        - remaining: Time remaining
        """
        if not self.ha_available:
            period = "day" if is_day else "night"
            logger.info(f"[SIMULATION] Would fire progress event: {period} at {threshold}% (actual: {progress:.1f}%)")
            return False
        
        try:
            period = "day" if is_day else "night"
            data = {
                "period": period,
                "progress": round(progress, 1),
                "threshold": threshold,
                "timestamp": self._get_now().isoformat(),
                **(event_data or {})
            }
            
            response = requests.post(
                f"{self.supervisor_url}/events/{self.PROGRESS_EVENT_TYPE}",
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Progress event fired: {period} at {threshold}% (actual: {progress:.1f}%)")
                return True
            else:
                logger.error(f"Failed to fire progress event: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error firing progress event: {e}")
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
            "day_progress": "mdi:progress-clock",
            "night_progress": "mdi:moon-waning-crescent",
            "is_day": "mdi:white-balance-sunny",
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
    
    def _calculate_progress(self) -> Optional[dict]:
        """
        Calculate current day or night progress.
        Returns dict with progress info or None if unavailable.
        """
        if not self._solar_info:
            return None
        
        solar_info = self._solar_info
        if not solar_info.sunrise or not solar_info.sunset:
            return None
        
        now = self._get_now()
        is_day = solar_info.sunrise <= now <= solar_info.sunset
        
        if is_day:
            total = (solar_info.sunset - solar_info.sunrise).total_seconds()
            elapsed = (now - solar_info.sunrise).total_seconds()
            progress = (elapsed / total * 100) if total > 0 else 0
            remaining = (solar_info.sunset - now).total_seconds()
            
            return {
                "is_day": True,
                "progress": min(100, max(0, progress)),
                "elapsed_seconds": int(elapsed),
                "remaining_seconds": int(remaining),
                "total_seconds": int(total),
                "start_time": solar_info.sunrise,
                "end_time": solar_info.sunset,
            }
        else:
            # Night - calculate from sunset to next sunrise
            if now > solar_info.sunset:
                # After sunset
                next_sunrise = solar_info.sunrise + timedelta(days=1)
                start_time = solar_info.sunset
                end_time = next_sunrise
                total = (next_sunrise - solar_info.sunset).total_seconds()
                elapsed = (now - solar_info.sunset).total_seconds()
            else:
                # Before sunrise
                prev_sunset = solar_info.sunset - timedelta(days=1)
                start_time = prev_sunset
                end_time = solar_info.sunrise
                total = (solar_info.sunrise - prev_sunset).total_seconds()
                elapsed = (now - prev_sunset).total_seconds()
            
            progress = (elapsed / total * 100) if total > 0 else 0
            remaining = total - elapsed
            
            return {
                "is_day": False,
                "progress": min(100, max(0, progress)),
                "elapsed_seconds": int(elapsed),
                "remaining_seconds": int(max(0, remaining)),
                "total_seconds": int(total),
                "start_time": start_time,
                "end_time": end_time,
            }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def update_progress_sensors(self) -> None:
        """
        Update progress sensors and fire threshold events.
        Called periodically from the monitor loop.
        """
        progress_data = self._calculate_progress()
        if not progress_data:
            return
        
        is_day = progress_data["is_day"]
        progress = progress_data["progress"]
        elapsed = progress_data["elapsed_seconds"]
        remaining = progress_data["remaining_seconds"]
        
        # Detect day/night transition
        if self._last_is_day is not None and self._last_is_day != is_day:
            # Reset thresholds on transition
            if is_day:
                self._fired_day_thresholds.clear()
                logger.info("Day started - resetting day progress thresholds")
            else:
                self._fired_night_thresholds.clear()
                logger.info("Night started - resetting night progress thresholds")
        self._last_is_day = is_day
        
        # Update is_day sensor
        self.update_sensor("is_day", "on" if is_day else "off", {
            "device_class": "running",
            "period": "day" if is_day else "night"
        })
        
        # Update progress sensors
        if is_day:
            self.update_sensor("day_progress", f"{progress:.1f}", {
                "unit_of_measurement": "%",
                "progress_percent": round(progress, 1),
                "elapsed": self._format_duration(elapsed),
                "remaining": self._format_duration(remaining),
                "elapsed_seconds": elapsed,
                "remaining_seconds": remaining,
                "sunrise": progress_data["start_time"].isoformat(),
                "sunset": progress_data["end_time"].isoformat(),
            })
            # Set night progress to 0 during day
            self.update_sensor("night_progress", "0.0", {
                "unit_of_measurement": "%",
                "progress_percent": 0,
            })
            
            # Check and fire day threshold events
            fired_thresholds = self._fired_day_thresholds
        else:
            self.update_sensor("night_progress", f"{progress:.1f}", {
                "unit_of_measurement": "%",
                "progress_percent": round(progress, 1),
                "elapsed": self._format_duration(elapsed),
                "remaining": self._format_duration(remaining),
                "elapsed_seconds": elapsed,
                "remaining_seconds": remaining,
                "sunset": progress_data["start_time"].isoformat(),
                "sunrise": progress_data["end_time"].isoformat(),
            })
            # Set day progress to 0 during night
            self.update_sensor("day_progress", "0.0", {
                "unit_of_measurement": "%",
                "progress_percent": 0,
            })
            
            # Check and fire night threshold events
            fired_thresholds = self._fired_night_thresholds
        
        # Fire threshold events
        for threshold in self.PROGRESS_THRESHOLDS:
            if progress >= threshold and threshold not in fired_thresholds:
                event_data = {
                    "elapsed": self._format_duration(elapsed),
                    "remaining": self._format_duration(remaining),
                    "elapsed_seconds": elapsed,
                    "remaining_seconds": remaining,
                }
                self.fire_progress_event(is_day, progress, threshold, event_data)
                fired_thresholds.add(threshold)
    
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
        logger.info("Event monitor started (independent background process)")
        
        while self.running:
            try:
                # Check and fire phase events
                self.check_and_fire_events()
                
                # Update progress sensors and fire progress events
                self.update_progress_sensors()
                
                # Log activity every 10 minutes to confirm the service is running
                now = self._get_now()
                if now.minute % 10 == 0 and now.second < 30:
                    progress_data = self._calculate_progress()
                    if progress_data:
                        period = "Day" if progress_data["is_day"] else "Night"
                        logger.debug(f"Event monitor active - {period} progress: {progress_data['progress']:.1f}%")
                    
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
        # Ne pas utiliser daemon=True pour que le thread continue même sans requête Flask
        self.thread = threading.Thread(target=self._monitor_loop, daemon=False)
        self.thread.start()
        logger.info("HomeSolar Event Service started (background monitoring active)")
    
    def stop(self) -> None:
        """Stop the event monitoring service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("HomeSolar Event Service stopped")


# Global instance
event_service = HomeAssistantEventService()
