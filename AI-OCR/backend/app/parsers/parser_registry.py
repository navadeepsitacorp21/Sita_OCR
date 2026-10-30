from typing import Dict, Tuple, Optional
from app.parsers.base_parser import BaseParser
from app.parsers.cbc_parser import CBCParser
from app.parsers.lipid_parser import LipidParser
from app.parsers.thyroid_parser import ThyroidParser
from app.parsers.lft_parser import LFTParser
from app.parsers.kft_parser import KFTParser
from app.parsers.hba1c_parser import HbA1cParser
from app.parsers.vitamin_parser import VitaminParser


class ParserRegistry:
    """
    Parser Registry v1.3.2
    Routes report type and hospital layout to the appropriate BaseParser instance.
    """
    def __init__(self):
        self._cbc = CBCParser()
        self._lipid = LipidParser()
        self._thyroid = ThyroidParser()
        self._lft = LFTParser()
        self._kft = KFTParser()
        self._hba1c = HbA1cParser()
        self._vitamin = VitaminParser()

        self.registry: Dict[Tuple[str, str], BaseParser] = {
            ("CBC", "aster"): self._cbc,
            ("CBC", "labsmart"): self._cbc,
            ("CBC", "apollo"): self._cbc,
            ("CBC", "medplus"): self._cbc,
            ("CBC", "vijaya"): self._cbc,
            ("CBC", "thyrocare"): self._cbc,
            ("CBC", "dr_lal_pathlabs"): self._cbc,
            ("CBC", "generic"): self._cbc,

            ("LIPID_PROFILE", "generic"): self._lipid,
            ("THYROID_PROFILE", "generic"): self._thyroid,
            ("LIVER_FUNCTION_TEST", "generic"): self._lft,
            ("KIDNEY_FUNCTION_TEST", "generic"): self._kft,
            ("DIABETES_PROFILE", "generic"): self._hba1c,
            ("VITAMIN_PROFILE", "generic"): self._vitamin
        }

    def get_parser(self, report_type: str, hospital: str = "generic") -> BaseParser:
        clean_type = (report_type or "CBC").upper()
        clean_hosp = (hospital or "generic").lower()

        # Try specific (report_type, hospital) match
        if (clean_type, clean_hosp) in self.registry:
            return self.registry[(clean_type, clean_hosp)]

        # Try fallback (report_type, "generic") match
        if (clean_type, "generic") in self.registry:
            return self.registry[(clean_type, "generic")]

        # Default fallback to CBC parser
        return self._cbc


_GLOBAL_REGISTRY = None


def get_parser_registry() -> ParserRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ParserRegistry()
    return _GLOBAL_REGISTRY
