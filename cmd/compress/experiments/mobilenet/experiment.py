# Copyright 2024 Mari�n Lorinc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     LICENSE.txt file
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# experiment.py: Experiment testing inference on single layer of MobileNetV2 model. However, it can be used to test multiple layers
# independently.

import torch
from cgp.cgp_adapter import CGP
from cgp.cgp_configuration import CGPConfiguration
from models.adapters.model_adapter import ModelAdapter
from experiments.composite.experiment import MultiExperiment
from experiments.experiment import Experiment
from models.quantization import conv2d_selector
from models.selector import FilterSelector, FilterSelectorCombination, FilterSelectorCombinations
import argparse
import torch.nn as nn
import operator
from functools import reduce
from typing import List
from parse import parse
import os

class MobilenetExperiment(MultiExperiment):
    """
    A class to manage MobileNet experiments, extending the MultiExperiment class.
    Perform experiments on MobileNetV2 using different error thresholds.
    """    
    name = "mobilenet"
    thresholds = [250, 150, 100, 50, 25, 15, 10, 0]
    def __init__(self, 
                 config: CGPConfiguration, 
                 model_adapter: ModelAdapter, 
                 cgp: CGP,
                 dtype=torch.int8, 
                 input_layer_name="conv1", 
                 output_layer_name="conv2", 
                 mse_thresholds=thresholds,
                 prefix="",
                 suffix="",
                 prepare=True,
                 generate_all=False,
                 **kwargs) -> None:
        """
        Initialize the MobilenetExperiment class.

        Args:
            config (CGPConfiguration): Configuration for the CGP.
            model_adapter (ModelAdapter): Adapter for the model.
            cgp (CGP): CGP instance.
            dtype (torch.dtype, optional): Data type for the tensors. Defaults to torch.int8.
            input_layer_name (str, optional): Name of the input layer. Defaults to "conv1".
            output_layer_name (str, optional): Name of the output layer. Defaults to "conv2". Currently unused and should be set to input_layer_name.
            mse_thresholds (list, optional): List of MSE thresholds. Defaults to [250, 150, 100, 50, 25, 15, 10, 0].
            prefix (str, optional): Prefix for experiment names. Defaults to "".
            suffix (str, optional): Suffix for experiment names. Defaults to "".
            prepare (bool, optional): Whether to prepare filters automatically. Defaults to True.
            generate_all (bool, optional): Whether to generate filters for all layers. Defaults to False.
            **kwargs: Additional arguments.
        """        
        super().__init__(config, model_adapter, cgp, dtype, **kwargs)
        self.mse_thresholds = mse_thresholds
        self.prefix = prefix
        self.suffix = suffix
        self.input_layer_name = input_layer_name
        self.output_layer_name = output_layer_name
        self.generate_all = generate_all
        
        if prepare:
            self._prepare_filters()

    def _prepare_filters(self):
        """
        Prepare filters for the experiments.
        """        
        if self.generate_all:
            for name, layer in self._model_adapter.get_all_layers():
                for mse in self.mse_thresholds:
                    in_layer: nn.Conv2d = layer
                    for experiment in self.create_experiment(f"{self.prefix}{name}_to_{name}_mse_{mse}_{self.args['rows']}_{self.args['cols']}{self.suffix}", self._get_filters(name, name)):
                        experiment.config.set_output_count(in_layer.in_channels / in_layer.groups * in_layer.out_channels * reduce(operator.mul, in_layer.kernel_size))
                        experiment.config.set_mse_threshold(self.error_threshold_function(experiment.config.get_output_count(), error=mse))
                        experiment.config.set_row_count(self.args["rows"])
                        experiment.config.set_col_count(self.args["cols"])
                        experiment.config.set_look_back_parameter(self.args["cols"] + 1)
        else:
            for mse in self.mse_thresholds:
                in_layer: nn.Conv2d = self._model_adapter.get_layer(self.input_layer_name)
                for experiment in self.create_experiment(f"{self.prefix}{self.input_layer_name}_{self.output_layer_name}_mse_{mse}_{self.args['rows']}_{self.args['cols']}{self.suffix}", self._get_filters(self.input_layer_name, self.output_layer_name)):
                    experiment.config.set_output_count(in_layer.in_channels / in_layer.groups * in_layer.out_channels * reduce(operator.mul, in_layer.kernel_size))
                    experiment.config.set_mse_threshold(self.error_threshold_function(experiment.config.get_output_count(), error=mse))
                    experiment.config.set_row_count(self.args["rows"])
                    experiment.config.set_col_count(self.args["cols"])
                    experiment.config.set_look_back_parameter(self.args["cols"] + 1)

    def create_experiment_from_name(self, config: CGPConfiguration):
        """
        Create an experiment instance from the configuration name.

        Args:
            config (CGPConfiguration): Configuration for the CGP.

        Returns:
            Experiment: The created experiment instance.
        """        
        name = config.path.parent.name
        experiment = Experiment(config, self._model_adapter, self._cgp, self.dtype, depth=self._depth, allowed_mse_error=self._allowed_mse_error, **self.args)
        
        first_layer_start = name.index("features")
        second_layer_start = name.index("_features", first_layer_start + 1)
        second_layer_start_alternative = name.find("_to_features", first_layer_start + 1)
        second_layer_start_original_index = second_layer_start_alternative if second_layer_start_alternative != -1 else second_layer_start
        second_layer_start_index = second_layer_start_alternative + len("_to_") if second_layer_start_alternative != -1 else second_layer_start + 1
        mse_start = name.index("_mse", second_layer_start_index)
        
        prefix = name[:first_layer_start]
        experiment.input_layer_name = name[first_layer_start:second_layer_start_original_index]
        experiment.output_layer_name = name[second_layer_start_index:mse_start]
        rest = name[mse_start+1:]
        result = parse("mse_{mse}_{rows}_{cols}", rest)
        
        if not result:
            raise ValueError("invalid name " + name)
        
        mse = float(result["mse"])
        rows = int(result["rows"])
        cols = int(result["cols"])
        experiment.mse = mse
        experiment.rows = rows
        experiment.cols = cols
        experiment.prefix = prefix
        experiment.config.set_mse_threshold(experiment.error_threshold_function(experiment.config.get_output_count(), error=mse))
        experiment.config.set_row_count(rows)
        experiment.config.set_col_count(cols)
        experiment.config.set_look_back_parameter(cols + 1)
        experiment.set_feature_maps_combinations(self._get_filters(experiment.input_layer_name, experiment.output_layer_name))
        # self.rename_if_needed(experiment)
        return experiment

    def rename_if_needed(self, experiment: Experiment):
        """
        Rename the experiment folder if needed.

        Args:
            experiment (Experiment): The experiment instance.
        """        
        dirname = "{prefix}{input_layer_name}_{output_layer_name}_mse_{mse}_{rows}_{cols}".format(
            input_layer_name=experiment._model_adapter._to_implementation_name(experiment.input_layer_name),
            output_layer_name=experiment._model_adapter._to_implementation_name(experiment.output_layer_name),
            mse=experiment.mse,
            rows=experiment.rows,
            cols=experiment.cols,
            prefix=experiment.prefix
        )
        
        if experiment._model_adapter._to_implementation_name(experiment.input_layer_name) != experiment.input_layer_name \
            and experiment._model_adapter._to_implementation_name(experiment.output_layer_name) != experiment.output_layer_name:
            new_name = experiment.base_folder.parent / dirname
            print(f"renaming {experiment.base_folder} to {new_name}")
            os.rename(experiment.base_folder, new_name)
            experiment.set_paths(new_name)
            experiment.temporary_base_folder = None
            experiment.base_folder = new_name
            experiment.config.path = new_name / experiment.config.path.name

    def _get_filters(self, input_layer_names: List[str], output_layer_names: List[str]):
        """
        Get filter selectors for the specified layers.

        Args:
            input_layer_names (List[str]): List of input layer names.
            output_layer_names (List[str]): List of output layer names.

        Returns:
            FilterSelectorCombinations: The filter selector combinations.
        """        
        combinations = FilterSelectorCombinations()
        combination = FilterSelectorCombination()
        combination.add(FilterSelector(input_layer_names, [(slice(None), slice(None), slice(None), slice(None))], []))
        combination.add(FilterSelector(output_layer_names, [], [(slice(None), slice(None), slice(None), slice(None))]))
        combinations.add(combination)
        return combinations
