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
# optimize_model.py: Train CGP circuits locally.

from commands.factory.experiment import create_all_experiment
from experiments.experiment import MissingChromosomeError

def optimize_model(args):
    """
    Optimizes the model by training it using the Cartesian Genetic Programming (CGP) algorithm.

    Args:
        args: Parsed command-line arguments containing the necessary parameters for the optimization process.

    Workflow:
        1. Creates all experiments based on the provided arguments.
        2. Checks if the experiment has already completed the desired number of runs.
        3. If the experiment has not completed, it resumes training from the last run if applicable.
        4. Handles cases where the chromosome file is missing and continues training.
        5. Trains the experiment using the CGP algorithm.
    """    
    for experiment in create_all_experiment(args):
        # experiment.config.set_start_run(args.start_run)
        # experiment.config.set_start_generation(args.start_generation)
        experiment = experiment.get_isolated_train_env(args.experiment_env)
        last_run = experiment.get_number_of_experiment_results()
        
        if last_run == experiment.config.get_number_of_runs():
            print("skipping " + experiment.get_name())
            continue
        
        try:
            if last_run != 0:
                experiment = experiment.get_resumed_train_env()
        except MissingChromosomeError:
            pass
            
        experiment.train_cgp()
