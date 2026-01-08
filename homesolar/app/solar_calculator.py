"""
Calculateur solaire basé sur l'algorithme NOAA
Port Python pour l'add-on Home Assistant HomeSolar
"""

import math
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TwilightType(Enum):
    """Types de crépuscule"""
    SUNRISE = 0          # -0.833° (réfraction + diamètre solaire)
    CIVIL = 1            # -6°
    NAUTICAL = 2         # -12°
    ASTRONOMICAL = 3     # -18°


@dataclass
class SolarTimes:
    """Résultat des calculs solaires"""
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    solar_noon: Optional[datetime] = None
    is_polar_night: bool = False
    is_polar_day: bool = False
    
    @property
    def day_length(self) -> Optional[timedelta]:
        if self.sunrise and self.sunset:
            return self.sunset - self.sunrise
        return None


@dataclass
class CompleteSolarInfo:
    """Informations solaires complètes incluant tous les crépuscules"""
    date: datetime
    latitude: float
    longitude: float
    
    # Lever et coucher
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    solar_noon: Optional[datetime] = None
    
    # Crépuscules civils
    civil_dawn: Optional[datetime] = None
    civil_dusk: Optional[datetime] = None
    
    # Crépuscules nautiques
    nautical_dawn: Optional[datetime] = None
    nautical_dusk: Optional[datetime] = None
    
    # Crépuscules astronomiques
    astronomical_dawn: Optional[datetime] = None
    astronomical_dusk: Optional[datetime] = None
    
    # États spéciaux
    is_polar_night: bool = False
    is_polar_day: bool = False
    
    @property
    def day_length(self) -> Optional[timedelta]:
        if self.sunrise and self.sunset:
            return self.sunset - self.sunrise
        return None
    
    def get_human_readable_duration(self) -> str:
        """Durée formatée lisible"""
        duration = self.day_length
        if not duration:
            return "Nuit polaire" if self.is_polar_night else "Jour polaire"
        
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}min"
    
    def is_night(self) -> bool:
        """Est-ce actuellement la nuit ?"""
        now = datetime.now()
        
        if self.is_polar_night:
            return True
        if self.is_polar_day:
            return False
        
        if not self.sunrise or not self.sunset:
            return False
        
        return now < self.sunrise or now > self.sunset


class SolarCalculator:
    """
    Calculateur solaire basé sur l'équation académique de Wikipedia et NOAA
    Référence: https://en.wikipedia.org/wiki/Sunrise_equation
    """
    
    J2000 = 2451545.0
    EARTH_TILT = 23.4397  # Inclinaison axiale de la Terre en degrés
    
    @staticmethod
    def _get_solar_altitude(twilight_type: TwilightType) -> float:
        """Retourne l'altitude solaire pour un type de crépuscule"""
        altitudes = {
            TwilightType.SUNRISE: -0.833,
            TwilightType.CIVIL: -6.0,
            TwilightType.NAUTICAL: -12.0,
            TwilightType.ASTRONOMICAL: -18.0
        }
        return altitudes.get(twilight_type, -0.833)
    
    @staticmethod
    def _deg_to_rad(degrees: float) -> float:
        return degrees * math.pi / 180.0
    
    @staticmethod
    def _rad_to_deg(radians: float) -> float:
        return radians * 180.0 / math.pi
    
    @staticmethod
    def _ts_to_jd(unix_timestamp: float) -> float:
        """Convertit un timestamp Unix en Jour Julien"""
        return unix_timestamp / 86400.0 + 2440587.5
    
    @staticmethod
    def _jd_to_datetime(julian_day: float) -> datetime:
        """Convertit un Jour Julien en DateTime"""
        unix_time = (julian_day - 2440587.5) * 86400.0
        return datetime.utcfromtimestamp(unix_time)
    
    @classmethod
    def calculate(cls, date: datetime, latitude: float, longitude: float, 
                  twilight_type: TwilightType = TwilightType.SUNRISE) -> SolarTimes:
        """
        Calcule les heures solaires pour une date, position et type de crépuscule donnés
        """
        # Normaliser à minuit
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Convertir en timestamp Unix
        unix_epoch = datetime(1970, 1, 1)
        current_timestamp = (date - unix_epoch).total_seconds()
        
        # Calculer le Jour Julien
        jd = cls._ts_to_jd(current_timestamp)
        
        # Nombre de jours depuis J2000
        n = math.ceil(jd - cls.J2000 + 0.0009 - 69.184 / 86400.0)
        
        # Temps solaire moyen
        j_star = n + 0.0009 - longitude / 360.0
        
        # Anomalie moyenne du soleil
        M = (357.5291 + 0.98560028 * j_star) % 360.0
        M_rad = cls._deg_to_rad(M)
        
        # Équation du centre
        C = (1.9148 * math.sin(M_rad) + 
             0.0200 * math.sin(2 * M_rad) + 
             0.0003 * math.sin(3 * M_rad))
        
        # Longitude écliptique
        lambda_val = (M + C + 180.0 + 102.9372) % 360.0
        lambda_rad = cls._deg_to_rad(lambda_val)
        
        # Transit solaire (midi solaire)
        j_transit = (cls.J2000 + j_star + 
                    0.0053 * math.sin(M_rad) - 
                    0.0069 * math.sin(2 * lambda_rad))
        
        # Déclinaison du soleil
        sin_delta = math.sin(lambda_rad) * math.sin(cls._deg_to_rad(cls.EARTH_TILT))
        cos_delta = math.cos(math.asin(sin_delta))
        
        # Angle horaire
        solar_altitude = cls._get_solar_altitude(twilight_type)
        cos_omega = ((math.sin(cls._deg_to_rad(solar_altitude)) - 
                     math.sin(cls._deg_to_rad(latitude)) * sin_delta) / 
                    (math.cos(cls._deg_to_rad(latitude)) * cos_delta))
        
        # Vérifier les cas spéciaux (soleil de minuit / nuit polaire)
        if cos_omega > 1.0:
            # Nuit polaire - pas de lever de soleil
            return SolarTimes(
                solar_noon=cls._jd_to_datetime(j_transit),
                is_polar_night=True,
                is_polar_day=False
            )
        elif cos_omega < -1.0:
            # Soleil de minuit - pas de coucher de soleil
            return SolarTimes(
                solar_noon=cls._jd_to_datetime(j_transit),
                is_polar_night=False,
                is_polar_day=True
            )
        
        omega = math.acos(cos_omega)
        omega_deg = cls._rad_to_deg(omega)
        
        # Calculer lever et coucher
        j_rise = j_transit - omega_deg / 360.0
        j_set = j_transit + omega_deg / 360.0
        
        return SolarTimes(
            sunrise=cls._jd_to_datetime(j_rise),
            sunset=cls._jd_to_datetime(j_set),
            solar_noon=cls._jd_to_datetime(j_transit),
            is_polar_night=False,
            is_polar_day=False
        )
    
    @classmethod
    def get_complete_solar_info(cls, date: datetime, latitude: float, 
                                 longitude: float) -> CompleteSolarInfo:
        """
        Calcule toutes les informations solaires pour une date et position données
        """
        # Calculer le lever/coucher du soleil
        sunrise_times = cls.calculate(date, latitude, longitude, TwilightType.SUNRISE)
        
        # Calculer les crépuscules civils
        civil_times = cls.calculate(date, latitude, longitude, TwilightType.CIVIL)
        
        # Calculer les crépuscules nautiques
        nautical_times = cls.calculate(date, latitude, longitude, TwilightType.NAUTICAL)
        
        # Calculer les crépuscules astronomiques
        astronomical_times = cls.calculate(date, latitude, longitude, TwilightType.ASTRONOMICAL)
        
        return CompleteSolarInfo(
            date=date,
            latitude=latitude,
            longitude=longitude,
            sunrise=sunrise_times.sunrise,
            sunset=sunrise_times.sunset,
            solar_noon=sunrise_times.solar_noon,
            civil_dawn=civil_times.sunrise,
            civil_dusk=civil_times.sunset,
            nautical_dawn=nautical_times.sunrise,
            nautical_dusk=nautical_times.sunset,
            astronomical_dawn=astronomical_times.sunrise,
            astronomical_dusk=astronomical_times.sunset,
            is_polar_night=sunrise_times.is_polar_night,
            is_polar_day=sunrise_times.is_polar_day
        )


class CompleteSolarModel:
    """
    Modèle complet contenant les informations solaires pour le jour actuel
    et une projection sur une année complète.
    """
    
    def __init__(self, latitude: float, longitude: float, timezone_offset: int = 0):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_offset = timezone_offset
        
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        self.current_solar_info = SolarCalculator.get_complete_solar_info(
            current_date, latitude, longitude
        )
        
        # Appliquer le décalage horaire
        self._apply_timezone_offset(self.current_solar_info)
        
        # Générer les données pour chaque jour sur un an
        self.relative_map = {}
        next_year = current_date + timedelta(days=365)
        iteration_date = current_date - timedelta(days=2)
        
        while iteration_date.date() != next_year.date():
            iteration_date += timedelta(days=1)
            day_info = SolarCalculator.get_complete_solar_info(
                iteration_date, latitude, longitude
            )
            self._apply_timezone_offset(day_info)
            self.relative_map[iteration_date.date()] = day_info
    
    def _apply_timezone_offset(self, info: CompleteSolarInfo):
        """Applique le décalage horaire aux heures calculées"""
        offset = timedelta(hours=self.timezone_offset)
        
        if info.sunrise:
            info.sunrise = info.sunrise + offset
        if info.sunset:
            info.sunset = info.sunset + offset
        if info.solar_noon:
            info.solar_noon = info.solar_noon + offset
        if info.civil_dawn:
            info.civil_dawn = info.civil_dawn + offset
        if info.civil_dusk:
            info.civil_dusk = info.civil_dusk + offset
        if info.nautical_dawn:
            info.nautical_dawn = info.nautical_dawn + offset
        if info.nautical_dusk:
            info.nautical_dusk = info.nautical_dusk + offset
        if info.astronomical_dawn:
            info.astronomical_dawn = info.astronomical_dawn + offset
        if info.astronomical_dusk:
            info.astronomical_dusk = info.astronomical_dusk + offset
    
    def get_diff(self) -> timedelta:
        """Retourne la différence de durée d'ensoleillement par rapport à la veille"""
        yesterday = (self.current_solar_info.date - timedelta(days=1)).date()
        
        if yesterday in self.relative_map:
            yesterday_info = self.relative_map[yesterday]
            today_duration = self.current_solar_info.day_length
            yesterday_duration = yesterday_info.day_length
            
            if today_duration and yesterday_duration:
                return today_duration - yesterday_duration
        
        return timedelta(0)
    
    def get_sign(self) -> str:
        """Retourne le signe de la différence ('+' ou '-')"""
        duration = self.get_diff()
        return "-" if duration.total_seconds() < 0 else "+"
    
    def get_next_same(self) -> datetime:
        """Trouve le prochain jour avec la même durée d'ensoleillement"""
        current_duration = self.current_solar_info.day_length
        if not current_duration:
            return self.current_solar_info.date
        
        for date, info in sorted(self.relative_map.items()):
            if date <= self.current_solar_info.date.date():
                continue
            
            duration = info.day_length
            if duration:
                current_hours = int(current_duration.total_seconds() // 3600)
                current_minutes = int((current_duration.total_seconds() % 3600) // 60)
                info_hours = int(duration.total_seconds() // 3600)
                info_minutes = int((duration.total_seconds() % 3600) // 60)
                
                if info_hours == current_hours and info_minutes >= current_minutes:
                    return datetime.combine(date, datetime.min.time())
        
        return self.current_solar_info.date
    
    def get_duration_to_next(self) -> timedelta:
        """Retourne la durée jusqu'au prochain jour avec même durée d'ensoleillement"""
        next_date = self.get_next_same()
        return next_date - self.current_solar_info.date
    
    def get_chart_data(self) -> list:
        """Génère les données pour le graphique annuel"""
        chart_data = []
        
        for date, info in sorted(self.relative_map.items()):
            duration = info.day_length
            if duration:
                chart_data.append({
                    'date': date.isoformat(),
                    'duration_minutes': duration.total_seconds() / 60,
                    'duration_formatted': info.get_human_readable_duration(),
                    'sunrise': info.sunrise.strftime('%H:%M') if info.sunrise else None,
                    'sunset': info.sunset.strftime('%H:%M') if info.sunset else None
                })
        
        return chart_data
