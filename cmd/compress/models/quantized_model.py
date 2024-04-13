import copy
import torch
from models.base_model import BaseModel
from abc import ABC, abstractmethod
from typing import Self, Optional
from tqdm import tqdm

class QuantizedBaseModel(BaseModel, ABC):
    def __init__(self, model_path: str = None):
        super().__init__(model_path)

    @abstractmethod
    def _prepare(self):
        raise NotImplementedError()

    @abstractmethod
    def _convert(self):
        raise NotImplementedError()
    
    @abstractmethod
    def quantize(self, new_path: str = None, inline=True) -> Self:
        raise NotImplementedError()

    def load_unquantized(self, model_path: Optional[str] = None):
        return super().load(model_path)

    def load(self, model_path: Optional[str] = None):
        self.eval()
        self._prepare()
        self._convert()
        super().load(model_path)
        return self
    

    def ptq_quantization(self) -> Self:
        reference_model = copy.deepcopy(self)
        self.eval()
        self._prepare()

        # Calibrate
        with torch.inference_mode():
            _, val_loader = self.get_split_train_validation_loaders()
            with tqdm(val_loader, unit="Batch", total=len(val_loader), leave=True) as loader:
                for x, _ in loader:
                    self(x)
    
        self._convert()

        # 1 byte instead of 4 bytes for FP32
        assert self.conv1.weight().element_size() == 1
        assert self.conv2.weight().element_size() == 1
        assert reference_model.conv1.weight.element_size() == 4

    def qat_quantization(self):
        reference_model = copy.deepcopy(self)

        self.eval()
        self._prepare()
        self.fit()
        self.eval()
        self._convert()

        # 1 byte instead of 4 bytes for FP32
        assert self.conv1.weight().element_size() == 1
        assert self.conv2.weight().element_size() == 1
        assert reference_model.conv1.weight.element_size() == 4        