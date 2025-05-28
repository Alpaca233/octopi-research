import pyvisa as visa
from typing import Optional


class PM16:
    def __init__(self, address: Optional[str] = None) -> None:
        if address is None:
            # look for address that starts with "USB0"
            self.rm = visa.ResourceManager()
            resources = self.rm.list_resources()
            usb_resources = [r for r in resources if r.startswith("USB0")]
            if not usb_resources:
                raise RuntimeError("No USB0 devices found")
            self.pm = self.rm.open_resource(usb_resources[0])
        else:
            self.pm = address
        self.wavelength = 500
        self.averaging = 10
        self.set_unit("W")
        self.set_averaging(self.averaging)
        self.set_auto_range(True)
        self.set_wavelength(self.wavelength)

    def read(self) -> float:
        return float(self.pm.query("MEAS:POW?"))

    def set_wavelength(self, wavelength: int) -> None:
        self.wavelength = wavelength
        self.pm.write(f"SENS:CORR:WAV {wavelength}")

    def set_averaging(self, averaging: int) -> None:
        self.averaging = averaging
        self.pm.write(f"SENS:AVER {averaging}")

    def set_auto_range(self, auto_range: bool) -> None:
        if auto_range:
            self.pm.write("SENS:RANGE:AUTO ON")
        else:
            self.pm.write("SENS:RANGE:AUTO OFF")

    def set_unit(self, unit: str) -> None:
        self.pm.write(f"SENS:POW:UNIT {unit}")
