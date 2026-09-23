from abc import ABC, abstractmethod
from typing import List

from src.classifier.schema import RawItem
from src.utils.io import save_json


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, target_volume: int) -> List[RawItem]: ...

    def save(self, items: List[RawItem], path: str) -> None:
        save_json([item.model_dump() for item in items], path)
