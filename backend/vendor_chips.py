from typing import Dict, Optional
from pydantic import BaseModel


class MemoryChipSpec(BaseModel):
    part_number: str
    manufacturer: str
    technology: str
    density_gbit: float
    organization: str
    voltage_volts: float
    package_type: str
    pin_count: int
    max_transfer_rate_mt_s: int
    status: str


DDR_VENDOR_DATABASE: Dict[str, MemoryChipSpec] = {
    "MT41K512M8RH-125": MemoryChipSpec(
        part_number="MT41K512M8RH-125", manufacturer="Micron",
        technology="DDR3L", density_gbit=4.0, organization="512Mx8",
        voltage_volts=1.35, package_type="FBGA-78", pin_count=78,
        max_transfer_rate_mt_s=1600, status="Active",
    ),
    "K4A8G085WB-BCPB": MemoryChipSpec(
        part_number="K4A8G085WB-BCPB", manufacturer="Samsung",
        technology="DDR4", density_gbit=8.0, organization="1Gx8",
        voltage_volts=1.2, package_type="FBGA-78", pin_count=78,
        max_transfer_rate_mt_s=2400, status="Active",
    ),
    "M308R0880B0-CQWM": MemoryChipSpec(
        part_number="M308R0880B0-CQWM", manufacturer="SK Hynix",
        technology="DDR5", density_gbit=16.0, organization="2Gx8",
        voltage_volts=1.1, package_type="FBGA-96", pin_count=96,
        max_transfer_rate_mt_s=5600, status="Active",
    ),
}


def lookup_vendor_chip(part_number: str) -> Optional[MemoryChipSpec]:
    pn_clean = part_number.strip().upper()
    for key, spec in DDR_VENDOR_DATABASE.items():
        if pn_clean in key.upper():
            return spec
    return None
