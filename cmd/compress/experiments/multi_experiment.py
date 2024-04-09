import glob
from typing import Generator, Tuple
import torch
import contextlib
import os
from cgp.cgp_adapter import CGP
from cgp.cgp_configuration import CGPConfiguration
from experiments.simple_experiment import BaseExperiment
from models.base import BaseModel

class MultiExperiment(BaseExperiment):
    def __init__(self, experiment_folder: str, experiment_name: str, model: BaseModel, cgp: CGP, dtype=torch.int8) -> None:
        super().__init__(experiment_folder, experiment_name, model, cgp, dtype)
        self.experiments = set()

    def _set_experiment_name(self, experiment_name: str):
        self.experiment_root_path = self.experiment_folder_path / experiment_name
        self.configs = self.experiment_root_path / "cgp_configs"
        self.weights = self.experiment_root_path / "weights"

    def forward_filters(self):
        raise NotImplementedError()

    def forward_experiments(self):
        raise NotImplementedError()

    @contextlib.contextmanager
    def experiment_context(self, experiment_name: str) -> Generator[Tuple[str, CGPConfiguration], None, None]:
        old_name = self.experiment_name
        try:
            self.reset()
            self.forward_filters()
            self._set_experiment_name(os.path.join(old_name, experiment_name))
            self.experiments.add(experiment_name)
            yield self.experiment_root_path.name, self._cgp.config.clone()
        finally:
            self.reset()
            self._set_experiment_name(old_name)

    def evaluate_runs(self, experiment_name: str = None):
        experiments = [experiment_name] if experiment_name else self.forward_experiments()
        stats_file = self._get_statistics_file()
        for i, experiment in enumerate(experiments):
            if os.path.exists(self.experiment_folder_path / experiment):
                raise FileNotFoundError(self.experiment_folder_path / experiment_name)
            with self.experiment_context(experiment) as (experiment_name, _):
                df = super().evaluate_runs()
                df["experiment"] = experiment_name
                df.to_csv(stats_file, mode="a" if i == 0 else "w", header=i==0)

    def get_number_of_experiment_results(self) -> int:
        return len(glob.glob(f"{str(self._get_cgp_output_file())}.*"))

    def get_number_of_experiments(self) -> int:
        return sum([1 for obj in os.listdir(self.experiment_root_path) if os.path.isfile(self.experiment_root_path / obj)])