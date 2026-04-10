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
    elevation: float = 0.0  # Altitude en mètres au-dessus du niveau de la mer
    
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
    
    def is_night(self, current_time: datetime = None) -> bool:
        """Est-ce actuellement la nuit ?"""
        if current_time is None:
            current_time = datetime.now()
        
        if self.is_polar_night:
            return True
        if self.is_polar_day:
            return False
        
        if not self.sunrise or not self.sunset:
            return False
        
        return current_time < self.sunrise or current_time > self.sunset


class SolarCalculator:
    """
    Calculateur solaire basé sur l'équation académique de Wikipedia et NOAA
    Référence: https://en.wikipedia.org/wiki/Sunrise_equation
    """
    
    J2000 = 2451545.0
    EARTH_TILT = 23.4397  # Inclinaison axiale de la Terre en degrés
    
    @staticmethod
    def _get_solar_altitude(twilight_type: TwilightType, elevation: float = 0.0) -> float:
        """
        Retourne l'altitude solaire pour un type de crépuscule,
        ajustée pour la dépression de l'horizon due à l'élévation.
        
        La dépression de l'horizon est calculée par:
        dépression ≈ 0.0293 × √(élévation) en degrés
        
        Cette correction fait que le soleil se lève plus tôt et se couche
        plus tard quand l'observateur est en altitude.
        """
        altitudes = {
            TwilightType.SUNRISE: -0.833,
            TwilightType.CIVIL: -6.0,
            TwilightType.NAUTICAL: -12.0,
            TwilightType.ASTRONOMICAL: -18.0
        }
        base_altitude = altitudes.get(twilight_type, -0.833)
        
        # Calculer la dépression de l'horizon due à l'élévation
        # Formule: dépression (degrés) = 0.0293 * sqrt(altitude en mètres)
        # Cela correspond à environ 1.76 arcmin par racine de mètre
        if elevation > 0:
            horizon_depression = 0.0293 * math.sqrt(elevation)
            # On soustrait car une dépression de l'horizon équivaut à
            # un soleil qui atteint l'horizon apparent plus tôt/tard
            return base_altitude - horizon_depression
        
        return base_altitude
    
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
                  twilight_type: TwilightType = TwilightType.SUNRISE,
                  elevation: float = 0.0) -> SolarTimes:
        """
        Calcule les heures solaires pour une date, position et type de crépuscule donnés.
        
        Args:
            date: Date du calcul
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            twilight_type: Type de crépuscule (lever/civil/nautique/astronomique)
            elevation: Altitude en mètres au-dessus du niveau de la mer
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
        
        # Angle horaire (avec correction d'élévation)
        solar_altitude = cls._get_solar_altitude(twilight_type, elevation)
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
                                 longitude: float, elevation: float = 0.0) -> CompleteSolarInfo:
        """
        Calcule toutes les informations solaires pour une date et position données.
        
        Args:
            date: Date du calcul
            latitude: Latitude en degrés
            longitude: Longitude en degrés
            elevation: Altitude en mètres au-dessus du niveau de la mer
        """
        # Calculer le lever/coucher du soleil
        sunrise_times = cls.calculate(date, latitude, longitude, TwilightType.SUNRISE, elevation)
        
        # Calculer les crépuscules civils
        civil_times = cls.calculate(date, latitude, longitude, TwilightType.CIVIL, elevation)
        
        # Calculer les crépuscules nautiques
        nautical_times = cls.calculate(date, latitude, longitude, TwilightType.NAUTICAL, elevation)
        
        # Calculer les crépuscules astronomiques
        astronomical_times = cls.calculate(date, latitude, longitude, TwilightType.ASTRONOMICAL, elevation)
        
        return CompleteSolarInfo(
            date=date,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
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
    
    def __init__(self, latitude: float, longitude: float, timezone_offset: int = 0, elevation: float = 0.0, current_date: datetime = None):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_offset = timezone_offset
        self.elevation = elevation
        
        if current_date is None:
            current_date = datetime.now()
        
        # Convert timezone-aware datetime to naive datetime for calculations
        if current_date.tzinfo is not None:
            current_date = current_date.replace(tzinfo=None)
        
        current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        current_date_utc = current_date - timedelta(hours=self.timezone_offset)
        
        self.current_solar_info = SolarCalculator.get_complete_solar_info(
            current_date_utc, latitude, longitude, elevation
        )
        
        # Set the date to the local date for display purposes
        self.current_solar_info.date = current_date
        
        # Appliquer le décalage horaire
        self._apply_timezone_offset(self.current_solar_info)
        
        # Générer les données pour chaque jour sur un an
        self.relative_map = {}
        next_year = current_date + timedelta(days=365)
        iteration_date = current_date - timedelta(days=2)
        
        while iteration_date.date() != next_year.date():
            iteration_date += timedelta(days=1)
            iteration_date_utc = iteration_date - timedelta(hours=self.timezone_offset)
            day_info = SolarCalculator.get_complete_solar_info(
                iteration_date_utc, latitude, longitude, elevation
            )
            # Set the date to the local date
            day_info.date = iteration_date
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
        """Génère les données pour les graphiques annuels"""
        chart_data = []
        previous_duration = None
        
        for date, info in sorted(self.relative_map.items()):
            duration = info.day_length
            if duration:
                duration_seconds = int(duration.total_seconds())
                
                # Calculate diff from previous day
                diff_seconds = 0
                if previous_duration:
                    diff_seconds = duration_seconds - int(previous_duration.total_seconds())
                
                # Get seasonal color based on latitude and date
                color = self._get_seasonal_color(date, self.latitude)
                
                # Sunrise/sunset in minutes since midnight for line chart
                sunrise_minutes = None
                sunset_minutes = None
                if info.sunrise:
                    sunrise_minutes = info.sunrise.hour * 60 + info.sunrise.minute
                if info.sunset:
                    sunset_minutes = info.sunset.hour * 60 + info.sunset.minute
                
                chart_data.append({
                    'date': date.isoformat(),
                    'duration_seconds': duration_seconds,
                    'duration_minutes': duration.total_seconds() / 60,
                    'duration_formatted': info.get_human_readable_duration(),
                    'diff_seconds': diff_seconds,
                    'color': color,
                    'sunrise': info.sunrise.strftime('%H:%M') if info.sunrise else None,
                    'sunset': info.sunset.strftime('%H:%M') if info.sunset else None,
                    'sunrise_minutes': sunrise_minutes,
                    'sunset_minutes': sunset_minutes
                })
                
                previous_duration = duration
        
        return chart_data
    
    def _get_seasonal_color(self, date, latitude: float) -> str:
        """
        Calcule la couleur en fonction de la saison et de la zone géographique.
        
        Zones géographiques:
        - Polaire: |latitude| > 66.5° (cercle polaire)
        - Tempérée: 23.5° < |latitude| <= 66.5° (4 saisons)
        - Tropicale: |latitude| <= 23.5° (2 saisons: sèche/humide)
        
        L'hémisphère sud a les saisons inversées.
        """
        from datetime import date as date_type
        
        # Normalize date to work with day of year
        if isinstance(date, date_type):
            day_of_year = date.timetuple().tm_yday
        else:
            day_of_year = date.timetuple().tm_yday
        
        abs_lat = abs(latitude)
        is_southern = latitude < 0
        
        # Adjust day of year for southern hemisphere (6 months offset)
        if is_southern:
            day_of_year = (day_of_year + 182) % 365
        
        # Calculate seasonal progress (0-1 through the year)
        # Starting from winter solstice (around Dec 21 = day 355)
        # Adjusted to start from Jan 1 for simplicity
        seasonal_progress = day_of_year / 365.0
        
        # Determine zone and apply appropriate color scheme
        if abs_lat > 66.5:
            # POLAR ZONE: Extreme contrasts, icy blues to midnight sun gold
            return self._polar_color(seasonal_progress, day_of_year)
        elif abs_lat > 23.5:
            # TEMPERATE ZONE: Classic 4 seasons
            return self._temperate_color(seasonal_progress)
        else:
            # TROPICAL ZONE: 2 seasons (dry/wet), less variation
            return self._tropical_color(seasonal_progress)
    
    def _polar_color(self, progress: float, day_of_year: int) -> str:
        """
        Couleurs pour zones polaires.
        - Nuit polaire (hiver): Bleus profonds et violets
        - Jour polaire (été): Dorés et blancs lumineux
        """
        import math
        
        # Use sine wave for smooth transition
        # Peak at summer solstice (around day 172)
        angle = (day_of_year - 172) / 365.0 * 2 * math.pi
        factor = (math.cos(angle) + 1) / 2  # 0 = winter, 1 = summer
        
        if factor < 0.3:
            # Deep winter - polar night: deep blue/purple
            r = int(30 + factor * 50)
            g = int(40 + factor * 60)
            b = int(120 + factor * 80)
        elif factor < 0.5:
            # Spring transition: cyan to light blue
            t = (factor - 0.3) / 0.2
            r = int(80 + t * 100)
            g = int(150 + t * 80)
            b = int(200 - t * 20)
        elif factor < 0.7:
            # Summer - midnight sun: golden white
            t = (factor - 0.5) / 0.2
            r = int(180 + t * 75)
            g = int(200 + t * 55)
            b = int(150 - t * 50)
        else:
            # Autumn transition: orange to purple
            t = (factor - 0.7) / 0.3
            r = int(255 - t * 180)
            g = int(180 - t * 120)
            b = int(100 + t * 60)
        
        return f'rgba({r}, {g}, {b}, 0.85)'
    
    def _temperate_color(self, progress: float) -> str:
        """
        Couleurs pour zones tempérées - 4 saisons classiques.
        - Hiver (Dec-Feb): Bleus froids
        - Printemps (Mar-May): Verts frais
        - Été (Jun-Aug): Jaunes/oranges chauds
        - Automne (Sep-Nov): Rouges/bruns
        """
        # Shift progress so winter starts at 0
        # Jan 1 is roughly 10 days after winter solstice
        adjusted = (progress + 0.03) % 1.0
        
        if adjusted < 0.25:
            # Winter: Deep blue to light blue
            t = adjusted / 0.25
            r = int(60 + t * 40)
            g = int(100 + t * 80)
            b = int(180 + t * 40)
        elif adjusted < 0.5:
            # Spring: Light blue to vibrant green
            t = (adjusted - 0.25) / 0.25
            r = int(100 - t * 30)
            g = int(180 + t * 75)
            b = int(220 - t * 150)
        elif adjusted < 0.75:
            # Summer: Green to golden yellow/orange
            t = (adjusted - 0.5) / 0.25
            r = int(70 + t * 185)
            g = int(255 - t * 55)
            b = int(70 - t * 30)
        else:
            # Autumn: Orange to deep red/brown
            t = (adjusted - 0.75) / 0.25
            r = int(255 - t * 80)
            g = int(200 - t * 120)
            b = int(40 + t * 80)
        
        return f'rgba({r}, {g}, {b}, 0.85)'
    
    def _tropical_color(self, progress: float) -> str:
        """
        Couleurs pour zones tropicales - 2 saisons.
        - Saison sèche: Jaunes/oranges chauds
        - Saison humide: Verts luxuriants/turquoise
        Variation de durée du jour minimale, couleurs plus douces.
        """
        import math
        
        # Two seasons: use sine wave with period of 6 months
        angle = progress * 2 * math.pi
        factor = (math.sin(angle) + 1) / 2  # 0-1, two cycles per year
        
        if factor < 0.5:
            # Wet/monsoon season: Lush greens and teals
            t = factor / 0.5
            r = int(40 + t * 60)
            g = int(180 + t * 40)
            b = int(140 + t * 40)
        else:
            # Dry season: Warm yellows and soft oranges
            t = (factor - 0.5) / 0.5
            r = int(100 + t * 155)
            g = int(220 - t * 40)
            b = int(180 - t * 100)
        
        return f'rgba({r}, {g}, {b}, 0.85)'
