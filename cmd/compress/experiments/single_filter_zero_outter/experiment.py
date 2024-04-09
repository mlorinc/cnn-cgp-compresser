import torch
import operator
from functools import reduce
from cgp.cgp_adapter import CGP
from models.base import BaseModel
from experiments.experiment import conv2d_core, conv2d_outter, dequantize_per_tensor
from experiments.multi_experiment import MultiExperiment

class SingleFilterZeroOutterExperiment(MultiExperiment):
    name = "single_filter_zero_outter"
    def __init__(self, experiment_folder: str, model: BaseModel, cgp: CGP, dtype=torch.int8, layer_name = "conv1", experiment_name=None) -> None:
        super().__init__(experiment_folder, experiment_name or SingleFilterZeroOutterExperiment.name, model, cgp, dtype)        

        self.filters = [
            *[(i, j, self._get_filter("conv1", i, j)) for j in range(model.conv1.in_channels) for i in range(model.conv1.out_channels)],
            *[(i, j, self._get_filter("conv2", i, j)) for j in range(model.conv2.in_channels) for i in range(model.conv2.out_channels)]
        ]

        output_selectors = [
            *[(i, j, self._get_output_selectors("conv1", i, j)) for j in range(model.conv1.in_channels) for i in range(model.conv1.out_channels)],
            *[(i, j, self._get_output_selectors("conv2", i, j)) for j in range(model.conv2.in_channels) for i in range(model.conv2.out_channels)]
        ]

        for _, _, (layer_name, sub_output_selectors) in output_selectors:
            bias = self._get_bias(layer_name)
            fp32_weights = self._get_reconstruction_weights(layer_name)
            for output_selector in sub_output_selectors:
                w = fp32_weights[*output_selector]
                size = reduce(operator.mul, w.shape)
                fp32_weights[*output_selector] = dequantize_per_tensor(torch.zeros(size), w.q_scale(), w.q_zero_point())
            self._set_weights_bias(getattr(model, layer_name), fp32_weights, bias)

    def _get_filter(self, layer_name: str, filter_i: int, channel_i: int):
        return layer_name, [conv2d_core([filter_i, channel_i], 5, 3)], [*conv2d_outter([filter_i, channel_i], 5, 3)]

    def _get_output_selectors(self, layer_name: str, filter_i: int, channel_i: int):
        return layer_name, conv2d_outter([filter_i, channel_i], 5, 3)

    def forward_filters(self):
        pass

    def train(self):
        row = col = 5
        for i, j, sel in self.filters:
            with self.experiment_context(f"{sel[0]}_{i}_{j}_{row}_{col}") as (experiment_name, config):
                try:
                    print(f"training: {experiment_name}")
                    config.set_row_count(row)
                    config.set_col_count(col)
                    config.set_look_back_parameter(col)
                    self.add_filters(*sel)
                    super().train(config)
                except FileExistsError:
                    print(f"skipping {experiment_name}")
                    continue        


def init(experiment_folder: str, model: BaseModel, cgp: CGP, dtype=torch.int8, experiment_name=None):
    return SingleFilterZeroOutterExperiment(experiment_folder, model, cgp, dtype, experiment_name=experiment_name)
