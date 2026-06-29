# app/core/pci.py
from app.services.pci.pci_calculator import PCICalculator

_instance = None

def get_pci_calculator() -> PCICalculator:
    global _instance
    if _instance is None:
        _instance = PCICalculator.get_instance()
    return _instance