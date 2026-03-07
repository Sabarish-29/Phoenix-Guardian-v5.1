"""
test_adapter_registry.py

Unit tests for the Integration Adapter Registry.

Tests validate:
  - All adapters implement BaseIntegrationAdapter (polymorphism)
  - AdapterRegistry CRUD operations (register, get, list, count)
  - Open/Closed Principle (new adapters without changing existing code)
  - Demo mode send_message() returns AdapterResponse with success=True
  - health_check_all() covers all registered adapters
  - KeyError on unknown adapter_id
  - TypeError on non-adapter registration
"""

import asyncio
import pytest

from phoenix_guardian.integrations.adapter_registry import (
    AdapterInfo,
    AdapterMessage,
    AdapterRegistry,
    AdapterResponse,
    AdapterStatus,
    AthenaHealthAdapter,
    BaseIntegrationAdapter,
    CernerFHIRAdapter,
    EpicFHIRAdapter,
    IntegrationProtocol,
    MeditechAdapter,
    adapter_registry,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def fresh_registry():
    """Return a clean AdapterRegistry (not the module singleton)."""
    reg = AdapterRegistry()
    reg.register("epic_fhir", EpicFHIRAdapter(demo_mode=True))
    reg.register("cerner_fhir", CernerFHIRAdapter(demo_mode=True))
    reg.register("hl7_meditech", MeditechAdapter(demo_mode=True))
    return reg


@pytest.fixture
def sample_message():
    """Sample AdapterMessage for send_message() tests."""
    return AdapterMessage(
        payload={
            "resourceType": "Patient",
            "id": "test-patient-001",
            "name": [{"family": "Smith", "given": ["John"]}],
        },
        message_id="MSG-TEST-001",
        source="PhoenixGuardian",
        destination="EHR",
    )


# ── Polymorphism Tests ────────────────────────────────────────────

class TestPolymorphism:
    """Verify all adapters implement the BaseIntegrationAdapter contract."""

    @pytest.mark.parametrize("adapter_class", [
        EpicFHIRAdapter,
        CernerFHIRAdapter,
        MeditechAdapter,
        AthenaHealthAdapter,
    ])
    def test_is_abstract_base_subclass(self, adapter_class):
        adapter = adapter_class(demo_mode=True)
        assert isinstance(adapter, BaseIntegrationAdapter)

    @pytest.mark.parametrize("adapter_class", [
        EpicFHIRAdapter,
        CernerFHIRAdapter,
        MeditechAdapter,
        AthenaHealthAdapter,
    ])
    def test_has_all_required_methods(self, adapter_class):
        adapter = adapter_class(demo_mode=True)
        assert callable(getattr(adapter, "connect", None))
        assert callable(getattr(adapter, "send_message", None))
        assert callable(getattr(adapter, "health_check", None))
        assert callable(getattr(adapter, "get_info", None))

    @pytest.mark.parametrize("adapter_class", [
        EpicFHIRAdapter,
        CernerFHIRAdapter,
        MeditechAdapter,
        AthenaHealthAdapter,
    ])
    def test_get_info_returns_adapter_info(self, adapter_class):
        adapter = adapter_class(demo_mode=True)
        info = adapter.get_info()
        assert isinstance(info, AdapterInfo)
        assert info.adapter_id
        assert info.protocol in IntegrationProtocol.__members__.values()


# ── AdapterRegistry CRUD Tests ────────────────────────────────────

class TestAdapterRegistry:

    def test_register_and_get(self, fresh_registry):
        adapter = fresh_registry.get("epic_fhir")
        assert isinstance(adapter, EpicFHIRAdapter)

    def test_count_matches_registered(self, fresh_registry):
        assert fresh_registry.count() == 3

    def test_list_adapters_returns_all(self, fresh_registry):
        infos = fresh_registry.list_adapters()
        assert len(infos) == 3
        ids = {i.adapter_id for i in infos}
        assert "epic_fhir" in ids
        assert "cerner_fhir" in ids
        assert "hl7_meditech" in ids

    def test_is_registered_true(self, fresh_registry):
        assert fresh_registry.is_registered("epic_fhir") is True

    def test_is_registered_false(self, fresh_registry):
        assert fresh_registry.is_registered("nonexistent") is False

    def test_get_unknown_raises_key_error(self, fresh_registry):
        with pytest.raises(KeyError):
            fresh_registry.get("nonexistent_adapter")

    def test_register_non_adapter_raises_type_error(self, fresh_registry):
        with pytest.raises(TypeError):
            fresh_registry.register("bad", object())

    def test_repr_contains_adapter_ids(self, fresh_registry):
        r = repr(fresh_registry)
        assert "epic_fhir" in r
        assert "cerner_fhir" in r


# ── Open/Closed Principle Test ─────────────────────────────────────

class TestOpenClosedPrinciple:

    def test_register_new_adapter_without_changing_existing(self, fresh_registry):
        class DrChronoAdapter(BaseIntegrationAdapter):
            async def connect(self): return True
            async def send_message(self, m): return AdapterResponse(True, 200, "OK")
            async def health_check(self): return AdapterStatus.ACTIVE
            def get_info(self): return AdapterInfo(
                "drchrono", "DrChrono REST", IntegrationProtocol.REST,
                "DrChrono", AdapterStatus.ACTIVE
            )

        initial_count = fresh_registry.count()
        fresh_registry.register("drchrono", DrChronoAdapter())
        assert fresh_registry.count() == initial_count + 1
        assert fresh_registry.is_registered("drchrono")
        adapter = fresh_registry.get("drchrono")
        assert isinstance(adapter, BaseIntegrationAdapter)


# ── Demo Mode Functional Tests ────────────────────────────────────

class TestDemoMode:

    def test_epic_connect_demo(self):
        adapter = EpicFHIRAdapter(demo_mode=True)
        result = asyncio.run(adapter.connect())
        assert result is True

    def test_epic_send_message_demo(self, sample_message):
        adapter = EpicFHIRAdapter(demo_mode=True)
        response = asyncio.run(adapter.send_message(sample_message))
        assert isinstance(response, AdapterResponse)
        assert response.success is True
        assert response.status_code == 201
        assert response.correlation_id is not None

    def test_cerner_send_message_demo(self, sample_message):
        adapter = CernerFHIRAdapter(demo_mode=True)
        asyncio.run(adapter.connect())
        response = asyncio.run(adapter.send_message(sample_message))
        assert response.success is True
        assert response.correlation_id.startswith("CERNER-")

    def test_meditech_send_message_demo(self, sample_message):
        adapter = MeditechAdapter(demo_mode=True)
        response = asyncio.run(adapter.send_message(sample_message))
        assert response.success is True

    def test_health_check_returns_demo_status(self):
        for AdapterClass in [EpicFHIRAdapter, CernerFHIRAdapter, MeditechAdapter]:
            adapter = AdapterClass(demo_mode=True)
            status = asyncio.run(adapter.health_check())
            assert status == AdapterStatus.DEMO

    def test_health_check_all_covers_all_adapters(self, fresh_registry):
        results = asyncio.run(fresh_registry.health_check_all())
        assert len(results) == fresh_registry.count()
        for adapter_id, status in results.items():
            assert isinstance(status, AdapterStatus)


# ── Module Singleton Test ─────────────────────────────────────────

class TestModuleSingleton:

    def test_singleton_has_expected_adapters(self):
        assert adapter_registry.is_registered("epic_fhir")
        assert adapter_registry.is_registered("cerner_fhir")
        assert adapter_registry.is_registered("hl7_meditech")

    def test_singleton_count_at_least_three(self):
        assert adapter_registry.count() >= 3
