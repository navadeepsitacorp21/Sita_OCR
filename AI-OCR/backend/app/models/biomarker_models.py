from pydantic import BaseModel
from typing import Optional

class Biomarker(BaseModel):
    name: str
    value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    is_abnormal: bool = False
    category: Optional[str] = None
