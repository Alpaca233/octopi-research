"""Tests for Nikon Ti2 integration components."""

import pytest
from control.nikon_ti2 import (
    NikonTi2FilterWheel_Simulation,
    NikonFilterWheelException,
)


class TestNikonTi2FilterWheelSimulation:
    """Tests for NikonTi2FilterWheel_Simulation."""

    def test_initialize(self):
        """Test filter wheel initialization."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.is_initialized

    def test_available_filter_wheels(self):
        """Test available filter wheels returns single wheel."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.available_filter_wheels == [1]

    def test_set_and_get_position(self):
        """Test setting and getting filter wheel position."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.set_filter_wheel_position({1: 3})
        assert fw.get_filter_wheel_position() == {1: 3}

    def test_position_range(self):
        """Test filter wheel positions 1-6."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        for pos in range(1, 7):
            fw.set_filter_wheel_position({1: pos})
            assert fw.get_filter_wheel_position() == {1: pos}

    def test_get_filter_wheel_info(self):
        """Test getting filter wheel info."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        info = fw.get_filter_wheel_info(1)
        assert info.index == 1
        assert info.number_of_slots == 6

    def test_home(self):
        """Test homing resets position to 1."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.set_filter_wheel_position({1: 5})
        fw.home(1)
        assert fw.get_filter_wheel_position() == {1: 1}

    def test_delay_methods_return_none(self):
        """Test delay methods return None (hardware-controlled)."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        assert fw.get_delay_ms() is None
        assert fw.get_delay_offset_ms() is None
        fw.set_delay_ms(100)  # Should not raise
        fw.set_delay_offset_ms(50)  # Should not raise

    def test_close(self):
        """Test close method."""
        fw = NikonTi2FilterWheel_Simulation()
        fw.initialize([1])
        fw.close()
        assert not fw.is_initialized


from control.nikon_ti2 import (
    NikonTi2DIA_Simulation,
    NikonDIAException,
)


class TestNikonTi2DIASimulation:
    """Tests for NikonTi2DIA_Simulation."""

    def test_initialize(self):
        """Test DIA initialization."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.is_initialized

    def test_initial_state_is_off(self):
        """Test DIA starts in off state."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.get_state() is False

    def test_set_and_get_state(self):
        """Test turning DIA on and off."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_state(True)
        assert dia.get_state() is True

        dia.set_state(False)
        assert dia.get_state() is False

    def test_initial_intensity(self):
        """Test DIA starts at 0% intensity."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()
        assert dia.get_intensity() == 0.0

    def test_set_and_get_intensity(self):
        """Test setting intensity."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_intensity(50.0)
        assert dia.get_intensity() == 50.0

        dia.set_intensity(100.0)
        assert dia.get_intensity() == 100.0

    def test_intensity_clamped_to_range(self):
        """Test intensity is clamped to 0-100%."""
        dia = NikonTi2DIA_Simulation()
        dia.initialize_device()

        dia.set_intensity(-10.0)
        assert dia.get_intensity() == 0.0

        dia.set_intensity(150.0)
        assert dia.get_intensity() == 100.0

    def test_requires_initialization(self):
        """Test methods require initialization."""
        dia = NikonTi2DIA_Simulation()
        with pytest.raises(NikonDIAException):
            dia.get_state()


from control.nikon_ti2 import (
    NikonTi2Adapter_Simulation,
    NikonTi2Components,
)


class TestNikonTi2AdapterSimulation:
    """Tests for NikonTi2Adapter_Simulation."""

    def test_initialize_all_components(self):
        """Test initializing all components."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=True,
            use_filter_wheel=True,
            use_dia=True,
        )

        assert isinstance(components, NikonTi2Components)
        assert components.stage is not None
        assert components.pfs is not None
        assert components.filter_wheel is not None
        assert components.dia is not None

    def test_initialize_stage_only(self):
        """Test initializing only stage."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=False,
            use_filter_wheel=False,
            use_dia=False,
        )

        assert components.stage is not None
        assert components.pfs is None
        assert components.filter_wheel is None
        assert components.dia is None

    def test_initialize_nothing(self):
        """Test initializing no components."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=False,
            use_pfs=False,
            use_filter_wheel=False,
            use_dia=False,
        )

        assert components.stage is None
        assert components.pfs is None
        assert components.filter_wheel is None
        assert components.dia is None

    def test_components_are_initialized(self):
        """Test that returned components are already initialized."""
        adapter = NikonTi2Adapter_Simulation()
        components = adapter.initialize(
            use_stage=True,
            use_pfs=True,
            use_filter_wheel=True,
            use_dia=True,
        )

        # PFS, filter wheel, and DIA should be initialized
        assert components.pfs.is_initialized
        assert components.filter_wheel.is_initialized
        assert components.dia.is_initialized
