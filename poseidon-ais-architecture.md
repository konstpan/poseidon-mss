# Poseidon Maritime Security System
## AIS Data Architecture & Emulator Specification

**Version:** 1.0  
**Purpose:** Define source-agnostic AIS data ingestion with built-in traffic emulator

---

## 1. Architecture Overview

### Design Principles

**Source Abstraction:**
- Internal representation independent of data source
- Adapter pattern for different AIS sources
- Easy to add new sources without changing core logic
- Multi-source support with automatic failover

**Development Flexibility:**
- Built-in traffic emulator for offline development
- Reproducible test scenarios
- No external API dependencies during development
- Fast iteration cycles

**Production Readiness:**
- Support for port's own AIS receivers
- Multiple source failover
- Source quality metrics
- Cross-validation between sources

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIS INGESTION LAYER                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           AIS Message Processor (Core)                     │ │
│  │                                                            │ │
│  │  • Receives messages from any adapter                     │ │
│  │  • Validates message format and content                   │ │
│  │  • Converts to internal AISMessage format                 │ │
│  │  • Deduplicates across sources                           │ │
│  │  • Enriches with vessel metadata                         │ │
│  │  • Stores in database                                     │ │
│  │  • Broadcasts to WebSocket clients                       │ │
│  └────────────────────┬───────────────────────────────────────┘ │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────────┐ │
│  │           AIS Adapter Manager                              │ │
│  │                                                            │ │
│  │  • Manages multiple data sources                          │ │
│  │  • Implements failover logic                             │ │
│  │  • Health monitoring                                      │ │
│  │  • Load balancing (if multiple sources)                  │ │
│  │  • Source priority management                            │ │
│  └─────┬──────────────────┬──────────────────┬──────────────┘ │
│        │                  │                  │                  │
│    Primary           Secondary          Tertiary               │
│    Source            Source              Source                │
│                                                                 │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
    ┌─────┴────┬─────────────┴──────────┬───────┴────────┬───────┐
    │          │                        │                │       │
┌───▼────┐ ┌──▼──────┐ ┌──────────▼────────┐ ┌─────▼──────┐ ┌──▼────┐
│Emulator│ │ AISHub  │ │ MarineTraffic     │ │Port Own    │ │UDP/TCP│
│(Test)  │ │ API     │ │ API               │ │Receiver    │ │Stream │
│        │ │         │ │                   │ │(NMEA)      │ │       │
└────────┘ └─────────┘ └───────────────────┘ └────────────┘ └───────┘
```

---

## 3. Internal Data Model

### 3.1 AISMessage Dataclass

**Purpose:** Source-agnostic internal representation of AIS data

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class NavigationStatus(Enum):
    UNDERWAY_ENGINE = "underway_engine"
    AT_ANCHOR = "at_anchor"
    NOT_UNDER_COMMAND = "not_under_command"
    RESTRICTED_MANEUVERABILITY = "restricted_maneuverability"
    CONSTRAINED_BY_DRAFT = "constrained_by_draft"
    MOORED = "moored"
    AGROUND = "aground"
    ENGAGED_IN_FISHING = "engaged_in_fishing"
    UNDERWAY_SAILING = "underway_sailing"
    UNKNOWN = "unknown"

class VesselType(Enum):
    CARGO = "cargo"
    TANKER = "tanker"
    PASSENGER = "passenger"
    FISHING = "fishing"
    MILITARY = "military"
    PLEASURE_CRAFT = "pleasure_craft"
    HIGH_SPEED_CRAFT = "high_speed_craft"
    TUG = "tug"
    PILOT_VESSEL = "pilot_vessel"
    SEARCH_AND_RESCUE = "search_and_rescue"
    OTHER = "other"
    UNKNOWN = "unknown"

@dataclass
class AISMessage:
    """Source-agnostic AIS message representation"""
    
    # Required fields
    mmsi: int
    timestamp: datetime
    latitude: float
    longitude: float
    
    # Navigation data (optional but usually present)
    speed_over_ground: Optional[float] = None  # knots
    course_over_ground: Optional[float] = None  # degrees 0-360
    heading: Optional[int] = None  # degrees 0-359
    rate_of_turn: Optional[float] = None  # degrees per minute
    
    # Status
    navigation_status: Optional[NavigationStatus] = None
    navigation_status_code: Optional[int] = None
    
    # Vessel static data (from Type 5 messages or enrichment)
    vessel_name: Optional[str] = None
    vessel_type: Optional[VesselType] = None
    vessel_type_code: Optional[int] = None
    call_sign: Optional[str] = None
    imo_number: Optional[int] = None
    
    # Vessel dimensions
    length: Optional[float] = None  # meters
    width: Optional[float] = None  # meters
    draft: Optional[float] = None  # meters
    
    # Position accuracy
    position_accuracy: str = 'L'  # 'H' = high (<10m), 'L' = low (>10m)
    
    # Data source metadata
    source: str = 'unknown'  # 'aishub', 'emulator', 'port_receiver', etc.
    source_quality: float = 1.0  # 0.0-1.0 confidence in data
    raw_message: Optional[str] = None  # Original message for debugging
    
    # Reception metadata
    received_at: datetime = None  # When system received it
    
    def __post_init__(self):
        if self.received_at is None:
            self.received_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'mmsi': self.mmsi,
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.latitude,
            'longitude': self.longitude,
            'speed_over_ground': self.speed_over_ground,
            'course_over_ground': self.course_over_ground,
            'heading': self.heading,
            'navigation_status': self.navigation_status.value if self.navigation_status else None,
            'vessel_name': self.vessel_name,
            'vessel_type': self.vessel_type.value if self.vessel_type else None,
            'source': self.source,
            'source_quality': self.source_quality
        }
```

---

## 4. Adapter Interface

### 4.1 Base Adapter (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class BoundingBox:
    """Geographic bounding box"""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

@dataclass
class SourceInfo:
    """Metadata about data source"""
    name: str
    type: str
    is_active: bool
    last_successful_fetch: Optional[datetime]
    error_count: int
    total_messages_received: int
    average_latency_seconds: float
    quality_score: float  # 0.0-1.0

class AISDataAdapter(ABC):
    """Abstract base class for all AIS data sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'unknown')
        self.is_enabled = config.get('enabled', True)
        self._error_count = 0
        self._last_fetch_time: Optional[datetime] = None
        
    @abstractmethod
    async def fetch_data(self, bbox: Optional[BoundingBox] = None) -> List[AISMessage]:
        """
        Fetch AIS data from source
        
        Args:
            bbox: Optional bounding box to filter results
            
        Returns:
            List of AISMessage objects
            
        Raises:
            AISDataFetchError: If fetch fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if data source is available and healthy
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_source_info(self) -> SourceInfo:
        """
        Get metadata about this data source
        
        Returns:
            SourceInfo object with current statistics
        """
        pass
    
    async def start(self):
        """Optional: Initialize adapter (e.g., open connections)"""
        pass
    
    async def stop(self):
        """Optional: Cleanup adapter (e.g., close connections)"""
        pass
    
    def _record_success(self, message_count: int):
        """Internal: Record successful fetch"""
        self._last_fetch_time = datetime.utcnow()
        self._error_count = 0
        
    def _record_error(self):
        """Internal: Record failed fetch"""
        self._error_count += 1
```

---

## 5. Concrete Adapters

### 5.1 Emulator Adapter

```python
class EmulatorAdapter(AISDataAdapter):
    """
    Traffic emulator for development and testing
    Generates realistic vessel movements and scenarios
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.scenario_file = config.get('scenario_file')
        self.num_vessels = config.get('num_vessels', 50)
        self.update_interval = config.get('update_interval_seconds', 30)
        self.emulator: Optional[TrafficEmulator] = None
        
    async def start(self):
        """Initialize emulator with scenario or random traffic"""
        from app.emulator.engine import TrafficEmulator
        from app.emulator.scenarios import load_scenario
        
        self.emulator = TrafficEmulator()
        
        if self.scenario_file:
            scenario = load_scenario(self.scenario_file)
            await self.emulator.load_scenario(scenario)
        else:
            # Generate random traffic
            bbox = BoundingBox(
                min_lat=40.60, max_lat=40.68,
                min_lon=22.90, max_lon=23.00
            )
            await self.emulator.generate_random_traffic(self.num_vessels, bbox)
        
        await self.emulator.start()
        
    async def fetch_data(self, bbox: Optional[BoundingBox] = None) -> List[AISMessage]:
        """Get current emulated vessel positions"""
        if not self.emulator or not self.emulator.is_running:
            return []
        
        messages = await self.emulator.get_ais_messages()
        
        # Filter by bounding box if provided
        if bbox:
            messages = [
                msg for msg in messages
                if bbox.min_lat <= msg.latitude <= bbox.max_lat
                and bbox.min_lon <= msg.longitude <= bbox.max_lon
            ]
        
        self._record_success(len(messages))
        return messages
    
    async def health_check(self) -> bool:
        """Emulator is always healthy if running"""
        return self.emulator is not None and self.emulator.is_running
    
    def get_source_info(self) -> SourceInfo:
        vessel_count = len(self.emulator.vessels) if self.emulator else 0
        return SourceInfo(
            name=self.name,
            type='emulator',
            is_active=self.emulator.is_running if self.emulator else False,
            last_successful_fetch=self._last_fetch_time,
            error_count=self._error_count,
            total_messages_received=vessel_count,
            average_latency_seconds=0.0,  # Instant
            quality_score=1.0  # Perfect simulated data
        )
    
    async def stop(self):
        """Stop emulator"""
        if self.emulator:
            await self.emulator.stop()
```

### 5.2 AISHub Adapter

```python
class AISHubAdapter(AISDataAdapter):
    """Adapter for AISHub API (https://www.aishub.net/)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config['api_key']
        self.api_url = config.get('api_url', 'http://data.aishub.net/ws.php')
        self.timeout = config.get('timeout_seconds', 30)
        
    async def fetch_data(self, bbox: Optional[BoundingBox] = None) -> List[AISMessage]:
        """Fetch data from AISHub API"""
        import aiohttp
        from pyais import decode
        
        params = {
            'username': self.api_key,
            'format': '1',  # JSON format
            'output': 'json'
        }
        
        if bbox:
            params.update({
                'latmin': bbox.min_lat,
                'latmax': bbox.max_lat,
                'lonmin': bbox.min_lon,
                'lonmax': bbox.max_lon
            })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url, 
                    params=params, 
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        raise AISDataFetchError(f"AISHub returned {response.status}")
                    
                    data = await response.json()
                    messages = self._parse_aishub_response(data)
                    self._record_success(len(messages))
                    return messages
                    
        except Exception as e:
            self._record_error()
            raise AISDataFetchError(f"AISHub fetch failed: {str(e)}")
    
    def _parse_aishub_response(self, data: dict) -> List[AISMessage]:
        """Convert AISHub JSON to AISMessage objects"""
        messages = []
        
        for vessel in data.get('vessels', []):
            try:
                msg = AISMessage(
                    mmsi=int(vessel['MMSI']),
                    timestamp=datetime.fromisoformat(vessel['TIME']),
                    latitude=float(vessel['LATITUDE']),
                    longitude=float(vessel['LONGITUDE']),
                    speed_over_ground=float(vessel.get('SOG', 0)),
                    course_over_ground=float(vessel.get('COG', 0)),
                    heading=int(vessel.get('HEADING', 0)),
                    vessel_name=vessel.get('NAME'),
                    vessel_type_code=int(vessel.get('TYPE', 0)),
                    source='aishub',
                    source_quality=0.9
                )
                messages.append(msg)
            except (KeyError, ValueError) as e:
                # Skip malformed messages
                continue
        
        return messages
    
    async def health_check(self) -> bool:
        """Check if AISHub API is responsive"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url, 
                    params={'username': self.api_key, 'format': '1'},
                    timeout=5
                ) as response:
                    return response.status == 200
        except:
            return False
    
    def get_source_info(self) -> SourceInfo:
        return SourceInfo(
            name=self.name,
            type='aishub_api',
            is_active=self.is_enabled,
            last_successful_fetch=self._last_fetch_time,
            error_count=self._error_count,
            total_messages_received=0,  # Would track in production
            average_latency_seconds=2.0,
            quality_score=0.9
        )
```

### 5.3 Port Receiver Adapter

```python
class PortReceiverAdapter(AISDataAdapter):
    """
    Adapter for port's own AIS receiver
    Supports NMEA over TCP/UDP or serial connection
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.receiver_url = config['receiver_url']  # tcp://host:port or udp://host:port
        self.protocol = config.get('protocol', 'tcp')
        self.buffer: List[AISMessage] = []
        self.connection = None
        
    async def start(self):
        """Establish connection to receiver"""
        if self.protocol == 'tcp':
            await self._connect_tcp()
        elif self.protocol == 'udp':
            await self._connect_udp()
            
    async def _connect_tcp(self):
        """Connect to TCP AIS receiver"""
        import asyncio
        # Implementation: Open TCP connection, start reading task
        pass
    
    async def fetch_data(self, bbox: Optional[BoundingBox] = None) -> List[AISMessage]:
        """Return buffered messages from receiver"""
        messages = self.buffer.copy()
        self.buffer.clear()
        
        if bbox:
            messages = [
                msg for msg in messages
                if bbox.min_lat <= msg.latitude <= bbox.max_lat
                and bbox.min_lon <= msg.longitude <= bbox.max_lon
            ]
        
        self._record_success(len(messages))
        return messages
    
    async def health_check(self) -> bool:
        """Check if connection is alive"""
        return self.connection is not None and not self.connection.is_closing()
    
    def get_source_info(self) -> SourceInfo:
        return SourceInfo(
            name=self.name,
            type='port_receiver',
            is_active=self.connection is not None,
            last_successful_fetch=self._last_fetch_time,
            error_count=self._error_count,
            total_messages_received=len(self.buffer),
            average_latency_seconds=0.5,  # Very low latency
            quality_score=1.0  # Direct from hardware
        )
```

---

## 6. Adapter Manager

```python
class AISAdapterManager:
    """
    Manages multiple AIS data sources with failover logic
    """
    
    def __init__(
        self, 
        primary_adapter: AISDataAdapter,
        secondary_adapter: Optional[AISDataAdapter] = None,
        tertiary_adapter: Optional[AISDataAdapter] = None
    ):
        self.adapters = [primary_adapter]
        if secondary_adapter:
            self.adapters.append(secondary_adapter)
        if tertiary_adapter:
            self.adapters.append(tertiary_adapter)
        
        self.active_adapter_index = 0
        self.failover_threshold = 3  # Failed attempts before failover
        
    async def start_all(self):
        """Initialize all adapters"""
        for adapter in self.adapters:
            try:
                await adapter.start()
            except Exception as e:
                logger.error(f"Failed to start adapter {adapter.name}: {e}")
    
    async def fetch_data(self, bbox: Optional[BoundingBox] = None) -> List[AISMessage]:
        """
        Fetch data from active adapter with automatic failover
        """
        for attempt in range(len(self.adapters)):
            adapter = self.adapters[self.active_adapter_index]
            
            try:
                # Check health first
                if not await adapter.health_check():
                    raise AISDataFetchError(f"{adapter.name} failed health check")
                
                # Fetch data
                messages = await adapter.fetch_data(bbox)
                
                # Deduplicate if using multiple sources
                messages = self._deduplicate_messages(messages)
                
                return messages
                
            except AISDataFetchError as e:
                logger.warning(f"Adapter {adapter.name} failed: {e}")
                
                # Try next adapter
                if attempt < len(self.adapters) - 1:
                    self.active_adapter_index = (self.active_adapter_index + 1) % len(self.adapters)
                    logger.info(f"Failing over to adapter {self.adapters[self.active_adapter_index].name}")
                else:
                    # All adapters failed
                    raise AISDataFetchError("All AIS data sources failed")
        
        return []
    
    def _deduplicate_messages(self, messages: List[AISMessage]) -> List[AISMessage]:
        """Remove duplicate messages (same MMSI, close timestamp)"""
        seen = {}
        unique = []
        
        for msg in messages:
            key = msg.mmsi
            if key not in seen:
                seen[key] = msg
                unique.append(msg)
            else:
                # Keep message with better quality
                if msg.source_quality > seen[key].source_quality:
                    seen[key] = msg
                    unique = [m for m in unique if m.mmsi != msg.mmsi]
                    unique.append(msg)
        
        return unique
    
    async def get_all_source_info(self) -> List[SourceInfo]:
        """Get status of all configured sources"""
        return [adapter.get_source_info() for adapter in self.adapters]
    
    async def stop_all(self):
        """Stop all adapters"""
        for adapter in self.adapters:
            await adapter.stop()
```

---

## 7. Traffic Emulator

### 7.1 Emulator Engine

```python
class TrafficEmulator:
    """
    Traffic emulator for generating realistic vessel movements
    Supports scenarios and random traffic generation
    """
    
    def __init__(self):
        self.vessels: List[EmulatedVessel] = []
        self.scenario: Optional[Scenario] = None
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        self.update_interval = 30  # seconds
        
    async def load_scenario(self, scenario: Scenario):
        """Load predefined scenario"""
        self.scenario = scenario
        self.vessels = []
        
        for vessel_config in scenario.vessels:
            vessel = EmulatedVessel.from_config(vessel_config)
            self.vessels.append(vessel)
        
        self.update_interval = scenario.update_interval
        
    async def generate_random_traffic(self, num_vessels: int, bbox: BoundingBox):
        """Generate random vessels in area"""
        import random
        
        self.vessels = []
        
        for i in range(num_vessels):
            mmsi = 999000000 + i
            lat = random.uniform(bbox.min_lat, bbox.max_lat)
            lon = random.uniform(bbox.min_lon, bbox.max_lon)
            speed = random.uniform(0, 15)
            course = random.uniform(0, 360)
            vessel_type = random.choice(list(VesselType))
            
            vessel = EmulatedVessel(
                mmsi=mmsi,
                name=f"EMULATED_{i:04d}",
                vessel_type=vessel_type,
                position=Position(lat, lon),
                speed=speed,
                course=course,
                behavior='straight'
            )
            self.vessels.append(vessel)
    
    async def start(self):
        """Start emulation"""
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        
    async def stop(self):
        """Stop emulation"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
            
    async def _update_loop(self):
        """Main update loop"""
        while self.is_running:
            await self.update_positions()
            await asyncio.sleep(self.update_interval)
    
    async def update_positions(self):
        """Calculate next positions for all vessels"""
        time_delta = timedelta(seconds=self.update_interval)
        
        for vessel in self.vessels:
            vessel.update_position(time_delta)
    
    async def get_ais_messages(self) -> List[AISMessage]:
        """Get current state as AIS messages"""
        messages = []
        
        for vessel in self.vessels:
            msg = vessel.to_ais_message()
            messages.append(msg)
        
        return messages
```

### 7.2 Emulated Vessel

```python
@dataclass
class Position:
    latitude: float
    longitude: float

class EmulatedVessel:
    """Represents an emulated vessel with movement behaviors"""
    
    def __init__(
        self,
        mmsi: int,
        name: str,
        vessel_type: VesselType,
        position: Position,
        speed: float,
        course: float,
        behavior: str = 'straight',
        **kwargs
    ):
        self.mmsi = mmsi
        self.name = name
        self.vessel_type = vessel_type
        self.position = position
        self.speed = speed  # knots
        self.course = course  # degrees
        self.heading = int(course)
        self.behavior = behavior
        self.waypoints = kwargs.get('waypoints', [])
        self.current_waypoint_index = 0
        self.loiter_center = position if behavior == 'loiter' else None
        self.loiter_radius = kwargs.get('loiter_radius', 0.1)  # nm
        self.start_time = datetime.utcnow()
        
    def update_position(self, time_delta: timedelta):
        """Calculate next position based on behavior"""
        if self.behavior == 'straight':
            self._update_straight(time_delta)
        elif self.behavior == 'loiter':
            self._update_loiter(time_delta)
        elif self.behavior == 'waypoints':
            self._update_waypoints(time_delta)
        elif self.behavior == 'evasive':
            self._update_evasive(time_delta)
    
    def _update_straight(self, time_delta: timedelta):
        """Simple dead reckoning - move in straight line"""
        hours = time_delta.total_seconds() / 3600
        distance_nm = self.speed * hours
        
        # Convert to degrees (approximate)
        lat_change = distance_nm * math.cos(math.radians(self.course)) / 60
        lon_change = distance_nm * math.sin(math.radians(self.course)) / (60 * math.cos(math.radians(self.position.latitude)))
        
        self.position.latitude += lat_change
        self.position.longitude += lon_change
        
        # Add slight random variation to course (more realistic)
        self.course += random.uniform(-2, 2)
        self.course = self.course % 360
        self.heading = int(self.course)
    
    def _update_loiter(self, time_delta: timedelta):
        """Minimal movement, slight drift in circular pattern"""
        if not self.loiter_center:
            self.loiter_center = self.position
        
        # Very slow speed
        self.speed = random.uniform(0.1, 0.8)
        
        # Slowly circle the loiter center
        hours = time_delta.total_seconds() / 3600
        angle_change = 10 * hours  # degrees per hour
        
        current_angle = math.atan2(
            self.position.longitude - self.loiter_center.longitude,
            self.position.latitude - self.loiter_center.latitude
        )
        
        new_angle = current_angle + math.radians(angle_change)
        
        self.position.latitude = self.loiter_center.latitude + (self.loiter_radius / 60) * math.cos(new_angle)
        self.position.longitude = self.loiter_center.longitude + (self.loiter_radius / 60) * math.sin(new_angle)
        
        self.course = (math.degrees(new_angle) + 90) % 360
        self.heading = int(self.course)
    
    def _update_waypoints(self, time_delta: timedelta):
        """Follow predefined waypoints"""
        if not self.waypoints or self.current_waypoint_index >= len(self.waypoints):
            # Finished waypoints, switch to straight
            self.behavior = 'straight'
            return
        
        target = self.waypoints[self.current_waypoint_index]
        
        # Calculate bearing to target
        lat1, lon1 = math.radians(self.position.latitude), math.radians(self.position.longitude)
        lat2, lon2 = math.radians(target[0]), math.radians(target[1])
        
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
        
        self.course = bearing
        self.heading = int(bearing)
        
        # Move toward target
        self._update_straight(time_delta)
        
        # Check if reached waypoint
        distance = self._calculate_distance(self.position, Position(target[0], target[1]))
        if distance < 0.05:  # Within 0.05 nm
            self.current_waypoint_index += 1
    
    def _update_evasive(self, time_delta: timedelta):
        """Random course changes (suspicious behavior)"""
        # Random course changes every update
        self.course += random.uniform(-45, 45)
        self.course = self.course % 360
        self.heading = int(self.course)
        
        # Variable speed
        self.speed += random.uniform(-2, 2)
        self.speed = max(1, min(20, self.speed))
        
        self._update_straight(time_delta)
    
    def _calculate_distance(self, pos1: Position, pos2: Position) -> float:
        """Calculate distance in nautical miles using Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lon1 = radians(pos1.latitude), radians(pos1.longitude)
        lat2, lon2 = radians(pos2.latitude), radians(pos2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        # Earth radius in nautical miles
        R = 3440.065
        
        return R * c
    
    def to_ais_message(self) -> AISMessage:
        """Convert emulated vessel to AIS message"""
        return AISMessage(
            mmsi=self.mmsi,
            timestamp=datetime.utcnow(),
            latitude=self.position.latitude,
            longitude=self.position.longitude,
            speed_over_ground=self.speed,
            course_over_ground=self.course,
            heading=self.heading,
            navigation_status=NavigationStatus.UNDERWAY_ENGINE if self.speed > 1 else NavigationStatus.AT_ANCHOR,
            vessel_name=self.name,
            vessel_type=self.vessel_type,
            source='emulator',
            source_quality=1.0
        )
    
    @classmethod
    def from_config(cls, config: dict) -> 'EmulatedVessel':
        """Create emulated vessel from configuration dict"""
        return cls(
            mmsi=config['mmsi'],
            name=config['name'],
            vessel_type=VesselType[config['type'].upper()],
            position=Position(config['start_position'][0], config['start_position'][1]),
            speed=config.get('speed', 10.0),
            course=config.get('course', 0.0),
            behavior=config.get('behavior', 'straight'),
            waypoints=config.get('waypoints', []),
            loiter_radius=config.get('loiter_radius', 0.1)
        )
```

---

## 8. Scenario Definition Format

### 8.1 YAML Scenario Structure

```yaml
# scenarios/collision_threat.yaml
name: "Collision Threat Scenario"
description: "Two cargo vessels on collision course"
duration_minutes: 30
update_interval: 30  # seconds between updates

vessels:
  - mmsi: 999000001
    name: "DEMO CARGO ALPHA"
    type: "cargo"
    start_position: [40.6401, 22.9000]  # [lat, lon]
    speed: 12.0  # knots
    course: 90  # degrees (heading East)
    behavior: "straight"
    
  - mmsi: 999000002
    name: "DEMO CARGO BETA"
    type: "cargo"
    start_position: [40.6401, 22.9500]
    speed: 10.0
    course: 270  # degrees (heading West - collision course!)
    behavior: "straight"

expected_alerts:
  - type: "collision_risk"
    severity: "critical"
    expected_after_seconds: 600  # Alert should trigger after 10 minutes
```

### 8.2 Scenario Loader

```python
import yaml
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Scenario:
    name: str
    description: str
    duration_minutes: int
    update_interval: int
    vessels: List[Dict[str, Any]]
    expected_alerts: List[Dict[str, Any]] = None

def load_scenario(filepath: str) -> Scenario:
    """Load scenario from YAML file"""
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    
    return Scenario(
        name=data['name'],
        description=data['description'],
        duration_minutes=data['duration_minutes'],
        update_interval=data.get('update_interval', 30),
        vessels=data['vessels'],
        expected_alerts=data.get('expected_alerts', [])
    )
```

---

## 9. Pre-built Scenarios

### 9.1 Normal Traffic (Development Default)

```yaml
# scenarios/thessaloniki_normal_traffic.yaml
name: "Thessaloniki Normal Traffic"
description: "Typical port traffic for development testing"
duration_minutes: 180  # 3 hours
update_interval: 30

vessels:
  - mmsi: 999000001
    name: "CARGO VESSEL 1"
    type: "cargo"
    start_position: [40.6200, 22.9100]
    speed: 8.0
    course: 45
    behavior: "straight"
    
  - mmsi: 999000002
    name: "TANKER 1"
    type: "tanker"
    start_position: [40.6400, 22.9300]
    speed: 5.0
    course: 180
    behavior: "straight"
    
  - mmsi: 999000003
    name: "PASSENGER FERRY"
    type: "passenger"
    start_position: [40.6300, 22.9200]
    waypoints:
      - [40.6350, 22.9250]
      - [40.6400, 22.9300]
      - [40.6450, 22.9350]
    speed: 15.0
    behavior: "waypoints"
    
  - mmsi: 999000004
    name: "FISHING BOAT 1"
    type: "fishing"
    start_position: [40.6100, 22.9000]
    speed: 0.5
    behavior: "loiter"
    loiter_radius: 0.2
    
  # ... 46 more vessels for realistic density
```

### 9.2 Zone Violation Scenario

```yaml
# scenarios/zone_violation.yaml
name: "Unauthorized Zone Entry"
description: "Fishing vessel enters restricted military zone"
duration_minutes: 20
update_interval: 30

vessels:
  - mmsi: 999000010
    name: "SUSPICIOUS FISHING"
    type: "fishing"
    start_position: [40.6280, 22.9280]  # Outside restricted zone
    waypoints:
      - [40.6300, 22.9300]  # Approaches zone
      - [40.6320, 22.9320]  # Enters restricted zone (alert!)
      - [40.6340, 22.9340]  # Deep inside
      - [40.6360, 22.9360]  # Exit zone
    speed: 5.0
    behavior: "waypoints"

expected_alerts:
  - type: "zone_violation"
    severity: "critical"
    zone_code: "THESS-RESTRICTED-ALPHA"
    expected_after_seconds: 300
```

### 9.3 Loitering Scenario

```yaml
# scenarios/loitering_suspicious.yaml
name: "Suspicious Loitering"
description: "Unknown vessel loitering near port entrance for extended period"
duration_minutes: 60
update_interval: 30

vessels:
  - mmsi: 999000020
    name: "UNKNOWN VESSEL"
    type: "other"
    start_position: [40.6250, 22.9100]
    speed: 0.3
    behavior: "loiter"
    loiter_radius: 0.05  # Very small radius (staying in place)

expected_alerts:
  - type: "loitering"
    severity: "medium"
    expected_after_seconds: 1800  # After 30 minutes
```

### 9.4 AIS Gap / Dark Vessel

```yaml
# scenarios/ais_gap_dark_vessel.yaml
name: "AIS Transmission Gap"
description: "Vessel stops transmitting AIS (going dark)"
duration_minutes: 30
update_interval: 30

vessels:
  - mmsi: 999000030
    name: "CARGO DARKSHIP"
    type: "cargo"
    start_position: [40.6300, 22.9200]
    speed: 10.0
    course: 90
    behavior: "straight"
    # Special: Stop transmitting after 10 minutes
    ais_gap:
      start_after_seconds: 600
      duration_seconds: 900  # 15 minutes dark

expected_alerts:
  - type: "ais_gap"
    severity: "high"
    expected_after_seconds: 1200  # 10 min + 10 min gap threshold
```

---

## 10. Configuration Management

### 10.1 Multi-Environment Configuration

```yaml
# config/ais_sources.yaml

development:
  primary_source:
    name: "Development Emulator"
    type: "emulator"
    enabled: true
    config:
      scenario_file: "scenarios/thessaloniki_normal_traffic.yaml"
      update_interval_seconds: 30
      num_vessels: 50
  
  secondary_source: null
  tertiary_source: null

testing:
  primary_source:
    name: "Test Emulator"
    type: "emulator"
    enabled: true
    config:
      scenario_file: null  # Use scenario specified in test
      update_interval_seconds: 10  # Faster for testing
  
  secondary_source:
    name: "AISHub Validation"
    type: "aishub"
    enabled: true
    config:
      api_key: "${AISHUB_API_KEY}"
      api_url: "http://data.aishub.net/ws.php"
      timeout_seconds: 30

staging:
  primary_source:
    name: "AISHub Production"
    type: "aishub"
    enabled: true
    config:
      api_key: "${AISHUB_API_KEY}"
  
  secondary_source:
    name: "MarineTraffic Backup"
    type: "marinetraffic"
    enabled: true
    config:
      api_key: "${MARINETRAFFIC_API_KEY}"

production:
  primary_source:
    name: "Port AIS Receiver"
    type: "port_receiver"
    enabled: true
    config:
      receiver_url: "tcp://ais-receiver.port.local:2000"
      protocol: "tcp"
      format: "nmea"
  
  secondary_source:
    name: "AISHub Fallback"
    type: "aishub"
    enabled: true
    config:
      api_key: "${AISHUB_API_KEY}"
  
  tertiary_source:
    name: "MarineTraffic Tertiary"
    type: "marinetraffic"
    enabled: true
    config:
      api_key: "${MARINETRAFFIC_API_KEY}"
```

### 10.2 Configuration Loader

```python
class AISSourceConfig:
    """Load and manage AIS source configuration"""
    
    @staticmethod
    def load_config(environment: str = 'development') -> Dict[str, Any]:
        """Load configuration for specified environment"""
        config_file = 'config/ais_sources.yaml'
        
        with open(config_file, 'r') as f:
            all_config = yaml.safe_load(f)
        
        env_config = all_config.get(environment)
        if not env_config:
            raise ValueError(f"No configuration for environment: {environment}")
        
        return env_config
    
    @staticmethod
    def create_adapters(environment: str = 'development') -> List[AISDataAdapter]:
        """Create adapter instances from configuration"""
        config = AISSourceConfig.load_config(environment)
        adapters = []
        
        for source_key in ['primary_source', 'secondary_source', 'tertiary_source']:
            source_config = config.get(source_key)
            if not source_config or not source_config.get('enabled'):
                continue
            
            adapter_type = source_config['type']
            adapter_config = source_config['config']
            adapter_config['name'] = source_config['name']
            
            adapter = AISSourceConfig._create_adapter(adapter_type, adapter_config)
            adapters.append(adapter)
        
        return adapters
    
    @staticmethod
    def _create_adapter(adapter_type: str, config: Dict[str, Any]) -> AISDataAdapter:
        """Factory method to create appropriate adapter"""
        if adapter_type == 'emulator':
            return EmulatorAdapter(config)
        elif adapter_type == 'aishub':
            return AISHubAdapter(config)
        elif adapter_type == 'marinetraffic':
            return MarineTrafficAdapter(config)
        elif adapter_type == 'port_receiver':
            return PortReceiverAdapter(config)
        else:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
```

---

## 11. Integration Example

### 11.1 Celery Task Using Adapter Manager

```python
from celery import Celery
from app.ais.manager import AISAdapterManager
from app.ais.config import AISSourceConfig
import os

celery = Celery('poseidon')

# Initialize adapter manager (once at startup)
environment = os.getenv('ENVIRONMENT', 'development')
adapters = AISSourceConfig.create_adapters(environment)
ais_manager = AISAdapterManager(*adapters)

@celery.on_after_configure.connect
async def setup_adapters(sender, **kwargs):
    """Start all adapters when Celery starts"""
    await ais_manager.start_all()

@celery.task
async def fetch_and_process_ais_data():
    """
    Fetch AIS data and process it
    This task runs every 60 seconds
    """
    try:
        # Fetch data from active source (with automatic failover)
        bbox = BoundingBox(
            min_lat=40.60, max_lat=40.68,
            min_lon=22.90, max_lon=23.00
        )
        messages = await ais_manager.fetch_data(bbox)
        
        logger.info(f"Fetched {len(messages)} AIS messages")
        
        # Process each message
        for msg in messages:
            await process_ais_message(msg)
        
    except AISDataFetchError as e:
        logger.error(f"Failed to fetch AIS data: {e}")
        # Alert monitoring system
        
async def process_ais_message(msg: AISMessage):
    """
    Process single AIS message (source-agnostic!)
    """
    from app.database import database
    from app.models import Vessel, VesselPosition
    
    # Update or create vessel record
    vessel = await database.get_or_create_vessel(msg.mmsi)
    if msg.vessel_name:
        vessel.name = msg.vessel_name
    if msg.vessel_type:
        vessel.vessel_type = msg.vessel_type.value
    vessel.last_seen = msg.timestamp
    await database.save(vessel)
    
    # Store position
    position = VesselPosition(
        mmsi=msg.mmsi,
        timestamp=msg.timestamp,
        latitude=msg.latitude,
        longitude=msg.longitude,
        speed_over_ground=msg.speed_over_ground,
        course_over_ground=msg.course_over_ground,
        heading=msg.heading,
        navigation_status=msg.navigation_status.value if msg.navigation_status else None,
        data_source=msg.source,
        source_quality=msg.source_quality
    )
    await database.save(position)
    
    # Broadcast to WebSocket clients
    await broadcast_position_update(msg.to_dict())
```

---

## 12. API Endpoints for Source Management

```python
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter(prefix="/api/v1/ais-sources", tags=["AIS Sources"])

@router.get("/status")
async def get_source_status():
    """Get status of all AIS data sources"""
    source_info = await ais_manager.get_all_source_info()
    return {
        "active_source": ais_manager.adapters[ais_manager.active_adapter_index].name,
        "sources": [info.__dict__ for info in source_info]
    }

@router.post("/switch/{source_name}")
async def switch_source(source_name: str):
    """Manually switch to a different data source"""
    for i, adapter in enumerate(ais_manager.adapters):
        if adapter.name == source_name:
            ais_manager.active_adapter_index = i
            return {"message": f"Switched to source: {source_name}"}
    
    raise HTTPException(404, f"Source not found: {source_name}")

@router.get("/emulator/scenarios")
async def list_scenarios():
    """List available emulator scenarios"""
    import os
    scenarios_dir = "scenarios"
    scenarios = [
        f.replace('.yaml', '') 
        for f in os.listdir(scenarios_dir) 
        if f.endswith('.yaml')
    ]
    return {"scenarios": scenarios}

@router.post("/emulator/load-scenario/{scenario_name}")
async def load_emulator_scenario(scenario_name: str):
    """Load a different scenario in emulator (if emulator is active)"""
    adapter = ais_manager.adapters[ais_manager.active_adapter_index]
    
    if not isinstance(adapter, EmulatorAdapter):
        raise HTTPException(400, "Active source is not emulator")
    
    from app.emulator.scenarios import load_scenario
    scenario = load_scenario(f"scenarios/{scenario_name}.yaml")
    
    await adapter.emulator.stop()
    await adapter.emulator.load_scenario(scenario)
    await adapter.emulator.start()
    
    return {"message": f"Loaded scenario: {scenario_name}"}
```

---

## 13. Benefits Summary

### For Development
- ✅ **Zero external dependencies** - Build entirely offline
- ✅ **Reproducible testing** - Same scenarios every time
- ✅ **Fast iteration** - No API delays or rate limits
- ✅ **Free** - No API costs during development

### For Testing
- ✅ **Controlled scenarios** - Test edge cases on demand
- ✅ **Validation** - Compare emulator vs real data
- ✅ **Load testing** - Simulate 500+ vessels easily
- ✅ **Automated testing** - Verify expected alerts trigger

### For Production
- ✅ **Source flexibility** - Use port's own equipment or APIs
- ✅ **Resilience** - Automatic failover between sources
- ✅ **Vendor independence** - Not locked to any provider
- ✅ **Quality tracking** - Monitor source reliability

### For Demonstrations
- ✅ **Impressive demos** - Show collision detection live
- ✅ **Training** - Teach operators with realistic scenarios
- ✅ **Portable** - Demo anywhere, no internet needed
- ✅ **Scenario library** - Collection of threat scenarios

---

**This architecture provides a robust, flexible foundation for AIS data ingestion that supports the entire development lifecycle from prototyping to production deployment.**