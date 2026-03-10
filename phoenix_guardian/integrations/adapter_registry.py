"""
adapter_registry.py

Integration Adapter Registry for Phoenix Guardian.

Implements the SAP Integration Suite adapter pattern:
  - BaseIntegrationAdapter: Abstract interface all EHR adapters implement
  - AdapterRegistry: Central pluggable catalog of all registered adapters
  - Concrete adapters: EpicFHIRAdapter, CernerFHIRAdapter, MeditechAdapter

SAP ALIGNMENT:
  This module mirrors the SAP Integration Suite (CPI/iFlow) adapter model:
    - SAP Integration Suite has adapters for SOAP, REST, OData, SFTP, HL7, FHIR
    - Each adapter implements the same interface (connect, send, health)
    - The iFlow configuration selects which adapter to use at runtime
    - Phoenix Guardian's AdapterRegistry does the same: select adapter by ID

DESIGN PATTERNS IMPLEMENTED:
  1. Abstract Factory (BaseIntegrationAdapter) — OOPS polymorphism
  2. Registry Pattern (AdapterRegistry) — central catalog with key→adapter lookup
  3. Open/Closed Principle — add new EHR systems by registering a new class;
     zero changes to existing orchestration code
  4. Strategy Pattern — different connection strategies, same calling interface
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ════════════════════════════════════════════════════════════════

class IntegrationProtocol(str, Enum):
    """Healthcare integration protocol identifiers."""
    FHIR_R4 = "FHIR_R4"
    HL7_V2 = "HL7_V2"
    REST = "REST"
    SOAP = "SOAP"
    ODATA = "ODATA"


class AdapterStatus(str, Enum):
    """Adapter connection health status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    DEMO = "DEMO"
    INITIALISING = "INITIALISING"


# ════════════════════════════════════════════════════════════════
# DATA CLASSES
# ════════════════════════════════════════════════════════════════

@dataclass
class AdapterMessage:
    """
    A message passed through an integration adapter.
    Mirrors the SAP Integration Suite message object.
    """
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    message_id: Optional[str] = None
    source: str = "PhoenixGuardian"
    destination: str = "EHR"


@dataclass
class AdapterResponse:
    """Response from an adapter send_message() call."""
    success: bool
    status_code: int
    message: str
    correlation_id: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass
class AdapterInfo:
    """Metadata about a registered adapter."""
    adapter_id: str
    display_name: str
    protocol: IntegrationProtocol
    system_type: str
    status: AdapterStatus
    version: str = "1.0"
    description: str = ""


# ════════════════════════════════════════════════════════════════
# ABSTRACT BASE CLASS
# ════════════════════════════════════════════════════════════════

class BaseIntegrationAdapter(ABC):
    """
    Abstract base class for all Phoenix Guardian integration adapters.

    SAP ALIGNMENT:
      Mirrors the adapter interface in SAP Integration Suite.
      Every adapter implements connect, send_message, health_check, get_info.

    POLYMORPHISM:
      All concrete adapters inherit this ABC and provide their own
      implementations. The AdapterRegistry and orchestration layer always
      call through this interface — they never know which specific EHR
      system they are talking to.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the EHR/integration system."""
        ...

    @abstractmethod
    async def send_message(self, message: AdapterMessage) -> AdapterResponse:
        """Send a business message to the EHR system."""
        ...

    @abstractmethod
    async def health_check(self) -> AdapterStatus:
        """Return current connection health status."""
        ...

    @abstractmethod
    def get_info(self) -> AdapterInfo:
        """Return metadata about this adapter."""
        ...

    def __repr__(self) -> str:
        info = self.get_info()
        return f"<{self.__class__.__name__} id={info.adapter_id!r} protocol={info.protocol.value}>"


# ════════════════════════════════════════════════════════════════
# CONCRETE ADAPTER IMPLEMENTATIONS
# ════════════════════════════════════════════════════════════════

class EpicFHIRAdapter(BaseIntegrationAdapter):
    """
    Adapter for Epic EHR systems via FHIR R4.

    Wraps the existing EpicConnector from phoenix_guardian.integrations.
    In demo mode, returns successful stubs without requiring a real endpoint.
    """

    def __init__(
        self,
        base_url: str = "https://epic-fhir-endpoint.example.com/api/FHIR/R4",
        client_id: str = "phoenix_guardian",
        demo_mode: bool = True,
    ) -> None:
        self._base_url = base_url
        self._client_id = client_id
        self._demo_mode = demo_mode
        self._connected = False
        logger.info("EpicFHIRAdapter initialised (demo_mode=%s)", demo_mode)

    async def connect(self) -> bool:
        if self._demo_mode:
            self._connected = True
            return True
        try:
            from .epic_connector import EpicConnector, EpicConfig
            config = EpicConfig(
                client_id=self._client_id,
                base_url=self._base_url,
                use_sandbox=True,
            )
            connector = EpicConnector(config)
            connector.connect()
            self._connected = True
            return True
        except Exception as exc:
            logger.error("EpicFHIRAdapter connect failed: %s", exc)
            self._connected = False
            return False

    async def send_message(self, message: AdapterMessage) -> AdapterResponse:
        logger.info("EpicFHIRAdapter: send_message (msg_id=%s, demo=%s)",
                     message.message_id, self._demo_mode)
        if self._demo_mode:
            return AdapterResponse(
                success=True,
                status_code=201,
                message="[DEMO] Epic FHIR R4 resource created",
                correlation_id=f"EPIC-{id(message):08X}",
            )
        return AdapterResponse(
            success=False, status_code=501,
            message="Epic live mode requires full OAuth2 configuration",
        )

    async def health_check(self) -> AdapterStatus:
        if self._demo_mode:
            return AdapterStatus.DEMO
        return AdapterStatus.ACTIVE if self._connected else AdapterStatus.INACTIVE

    def get_info(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id="epic_fhir",
            display_name="Epic EHR — FHIR R4",
            protocol=IntegrationProtocol.FHIR_R4,
            system_type="Epic",
            status=AdapterStatus.DEMO if self._demo_mode else (
                AdapterStatus.ACTIVE if self._connected else AdapterStatus.INACTIVE
            ),
            version="1.0",
            description="Epic FHIR R4 integration adapter. Most widely deployed EHR in US hospital systems.",
        )


class CernerFHIRAdapter(BaseIntegrationAdapter):
    """
    Adapter for Cerner/Oracle Health EHR via FHIR R4.

    Wraps the existing CernerConnector from phoenix_guardian.integrations.
    """

    def __init__(
        self,
        base_url: str = "https://fhir-myrecord.cerner.com/r4/",
        demo_mode: bool = True,
    ) -> None:
        self._base_url = base_url
        self._demo_mode = demo_mode
        self._connected = False

    async def connect(self) -> bool:
        if self._demo_mode:
            self._connected = True
            return True
        try:
            from .cerner_connector import CernerConnector, CernerConfig
            config = CernerConfig(base_url=self._base_url, use_sandbox=True)
            connector = CernerConnector(config)
            connector.connect()
            self._connected = True
            return True
        except Exception:
            return False

    async def send_message(self, message: AdapterMessage) -> AdapterResponse:
        logger.info("CernerFHIRAdapter: send_message (demo=%s)", self._demo_mode)
        if self._demo_mode:
            return AdapterResponse(
                success=True,
                status_code=201,
                message="[DEMO] Cerner FHIR R4 resource created",
                correlation_id=f"CERNER-{id(message):08X}",
            )
        return AdapterResponse(
            success=False, status_code=501,
            message="Cerner live mode not configured",
        )

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.DEMO if self._demo_mode else (
            AdapterStatus.ACTIVE if self._connected else AdapterStatus.INACTIVE
        )

    def get_info(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id="cerner_fhir",
            display_name="Cerner/Oracle Health — FHIR R4",
            protocol=IntegrationProtocol.FHIR_R4,
            system_type="Cerner",
            status=AdapterStatus.DEMO if self._demo_mode else AdapterStatus.ACTIVE,
            description="Cerner (Oracle Health) FHIR R4 adapter.",
        )


class MeditechAdapter(BaseIntegrationAdapter):
    """
    Adapter for Meditech EHR via HL7 v2 / REST.

    Wraps the existing MeditechConnector from phoenix_guardian.integrations.
    """

    def __init__(self, demo_mode: bool = True) -> None:
        self._demo_mode = demo_mode
        self._connected = False

    async def connect(self) -> bool:
        if self._demo_mode:
            self._connected = True
            return True
        return False

    async def send_message(self, message: AdapterMessage) -> AdapterResponse:
        logger.info("MeditechAdapter: send_message (HL7 v2, demo=%s)", self._demo_mode)
        if self._demo_mode:
            return AdapterResponse(
                success=True,
                status_code=200,
                message="[DEMO] Meditech HL7 v2 message sent",
                correlation_id=f"MEDITECH-{id(message):08X}",
            )
        return AdapterResponse(
            success=False, status_code=501,
            message="Meditech HL7 live mode not configured",
        )

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.DEMO if self._demo_mode else AdapterStatus.INACTIVE

    def get_info(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id="hl7_meditech",
            display_name="Meditech — HL7 v2",
            protocol=IntegrationProtocol.HL7_V2,
            system_type="Meditech",
            status=AdapterStatus.DEMO if self._demo_mode else AdapterStatus.INACTIVE,
            description="Meditech EHR HL7 v2 adapter for community hospitals.",
        )


class AthenaHealthAdapter(BaseIntegrationAdapter):
    """
    Adapter for athenahealth EHR via REST API.

    Wraps the existing AthenaHealthConnector from phoenix_guardian.integrations.
    """

    def __init__(self, demo_mode: bool = True) -> None:
        self._demo_mode = demo_mode
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def send_message(self, message: AdapterMessage) -> AdapterResponse:
        if self._demo_mode:
            return AdapterResponse(
                success=True, status_code=200,
                message="[DEMO] athenahealth REST API message sent",
                correlation_id=f"ATHENA-{id(message):08X}",
            )
        return AdapterResponse(
            success=False, status_code=501, message="Not configured",
        )

    async def health_check(self) -> AdapterStatus:
        return AdapterStatus.DEMO if self._demo_mode else AdapterStatus.ACTIVE

    def get_info(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id="athenahealth",
            display_name="athenahealth — REST API",
            protocol=IntegrationProtocol.REST,
            system_type="athenahealth",
            status=AdapterStatus.DEMO,
            description="athenahealth REST adapter for ambulatory care.",
        )


# ════════════════════════════════════════════════════════════════
# ADAPTER REGISTRY
# ════════════════════════════════════════════════════════════════

class AdapterRegistry:
    """
    Central adapter catalog for Phoenix Guardian integration layer.

    SAP ALIGNMENT:
      Mirrors the SAP Integration Suite adapter store. Adapters are
      registered by ID and retrieved by ID during agent orchestration.

    OPEN/CLOSED PRINCIPLE:
      To add a new EHR system: create NewEHRAdapter(BaseIntegrationAdapter),
      call registry.register("new_ehr", NewEHRAdapter()). Zero changes
      to existing orchestration code.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseIntegrationAdapter] = {}
        logger.info("AdapterRegistry initialised")

    def register(self, adapter_id: str, adapter: BaseIntegrationAdapter) -> None:
        """Register an adapter in the catalog."""
        if not isinstance(adapter, BaseIntegrationAdapter):
            raise TypeError(
                f"adapter must be a BaseIntegrationAdapter subclass, "
                f"got {type(adapter).__name__}"
            )
        self._adapters[adapter_id] = adapter
        info = adapter.get_info()
        logger.info("Integration adapter registered: %s (%s, %s)",
                     adapter_id, info.system_type, info.protocol.value)

    def get(self, adapter_id: str) -> BaseIntegrationAdapter:
        """Retrieve an adapter by ID."""
        if adapter_id not in self._adapters:
            available = list(self._adapters.keys())
            raise KeyError(
                f"Adapter '{adapter_id}' not registered. "
                f"Available adapters: {available}"
            )
        return self._adapters[adapter_id]

    def list_adapters(self) -> List[AdapterInfo]:
        """Return metadata for all registered adapters."""
        return [adapter.get_info() for adapter in self._adapters.values()]

    def is_registered(self, adapter_id: str) -> bool:
        """Return True if the adapter_id is registered."""
        return adapter_id in self._adapters

    def count(self) -> int:
        """Return the number of registered adapters."""
        return len(self._adapters)

    async def health_check_all(self) -> Dict[str, AdapterStatus]:
        """Run health_check() on all registered adapters."""
        results = {}
        for adapter_id, adapter in self._adapters.items():
            try:
                results[adapter_id] = await adapter.health_check()
            except Exception as exc:
                logger.warning("Health check failed for %s: %s", adapter_id, exc)
                results[adapter_id] = AdapterStatus.ERROR
        return results

    def __repr__(self) -> str:
        return f"<AdapterRegistry adapters={list(self._adapters.keys())}>"


# ════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON REGISTRY
# ════════════════════════════════════════════════════════════════

adapter_registry = AdapterRegistry()

adapter_registry.register("epic_fhir", EpicFHIRAdapter())
adapter_registry.register("cerner_fhir", CernerFHIRAdapter())
adapter_registry.register("hl7_meditech", MeditechAdapter())
adapter_registry.register("athenahealth", AthenaHealthAdapter())

logger.info("Phoenix Guardian Integration Adapter Registry ready (%d adapters)",
            adapter_registry.count())
