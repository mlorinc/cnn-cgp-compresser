import argparse
from experiments.all_layers.experiment import AllLayersExperiment
from experiments.grid_size.experiment import GridSizeExperiment 
from experiments.reversed_single_filter.experiment import ReversedSingleFilterExperiment
from experiments.single_channel.experiment import SingleChannelExperiment
from experiments.single_filter_zero_outter.experiment import SingleFilterZeroOutterExperiment
from experiments.single_filter.experiment import SingleFilterExperiment
from commands.optimize_prepare_model import optimize_prepare_model
from commands.optimize_model import optimize_model
from commands.evaluate_cgp_model import evaluate_cgp_model
from commands.train_model import train_model
from commands.evaluate_model import evaluate_model
from commands.quantize_model import quantize_model
from typing import List

experiments_classes = {
    AllLayersExperiment.name: AllLayersExperiment,
    GridSizeExperiment.name: GridSizeExperiment,
    ReversedSingleFilterExperiment.name: ReversedSingleFilterExperiment,
    SingleChannelExperiment.name: SingleChannelExperiment,
    SingleFilterZeroOutterExperiment.name: SingleFilterZeroOutterExperiment,
    SingleFilterExperiment.name: SingleFilterExperiment
}

experiment_factories = dict([(name, clazz.new) for name, clazz in experiments_classes.items()])
experiment_commands = ["train", "train-pbs", "evaluate"]

def _register_model_commands(subparsers: argparse._SubParsersAction):
    # model:train
    train_parser = subparsers.add_parser("model:train", help="Train a model")
    train_parser.add_argument("model_name", help="Name of the model to train")
    train_parser.add_argument("model_path", help="Path where trained model will be saved")
    train_parser.add_argument("-b", "--base", type=str, help="Path to the baseline model")

    # model:evaluate
    evaluate_parser = subparsers.add_parser("model:evaluate", help="Evaluate a model")
    evaluate_parser.add_argument("model_name", help="Name of the model to evaluate")
    evaluate_parser.add_argument("model_path", help="Path to the model to evaluate")

    # model:quantize
    quantize_parser = subparsers.add_parser("model:quantize", help="Quantize a model")
    quantize_parser.add_argument("model_name", help="Name of the model to quantize")
    quantize_parser.add_argument("model_path", help="Path where trained model is saved")
    quantize_parser.add_argument("new_path", help="Path of the new quantized model where it will be stored")    

def _register_experiment_commands(subparsers: argparse._SubParsersAction, experiment_names: List[str]):
    help_train = "Train a new CGP model to infer mising convolution weights from CNN model. Weights are trained as they are defined by {experiment_name}."
    help_evaluate = "Evaluate CGP model perfomance such as MSE, Energy, Area, Delay, Depth, Gate count and CNN accuracy and loss. Weights are trained as they are defined by {experiment_name}."
    help_metacentrum = "Prepare file structure and a PBS file for training in Metacentrum. Dataset is generated according to {experiment_name}."

    for command, help in zip(experiment_commands, [help_train, help_metacentrum, help_evaluate]):
        for experiment_name in experiment_names:
            experiment_parser = subparsers.add_parser(f"{experiment_name}:{command}", help=help.format(experiment_name=experiment_name))
            experiment_class = experiments_classes.get(experiment_name)
            experiment_parser.add_argument("model_name", help="Name of the model to optimize")
            experiment_parser.add_argument("model_path", help="Path to the model to optimize")
            experiment_parser.add_argument("cgp_binary_path", help="Path to the CGP binary")
            experiment_parser.add_argument("--start-run", nargs='?', type=int, default=0, help="From which run start evolution", required=False)
            experiment_parser.add_argument("--start-generation", nargs='?', type=int, default=0, help="From which generation start evolution", required=False)

            if command != "evaluate":
                experiment_parser.add_argument("--experiment-env", help="Create a new isolated environment", nargs="?", default="experiment_results")
            else:
                experiment_parser.add_argument("--file", nargs='+', help="List of file paths to evaluate", required=False)

            experiment_parser = experiment_class.get_argument_parser(experiment_parser)
            if "pbs" in command:
                experiment_parser = experiment_class.get_pbs_argument_parser(experiment_parser)                

            experiment_parser.set_defaults(factory=experiment_factories.get(experiment_name), experiment_name=experiment_name)

def register_commands(parser: argparse._SubParsersAction):
    subparsers = parser.add_subparsers(dest="command")
    _register_experiment_commands(subparsers, experiments_classes.keys())
    _register_model_commands(subparsers)

def dispatch(args):
    try:
        colon = args.command.index(":")
        experiment_name, command = args.command[:colon], args.command[colon+1:]
        print(experiment_name, command)
        if command == "train":
            return lambda: optimize_model(args)
        if command == "train-pbs":
            return lambda: optimize_prepare_model(args)
        if command == "evaluate":
            return lambda: evaluate_cgp_model(args)
        else:
            raise ValueError(f"unknown commmand {args.command}")
    except ValueError as e:
        if args.command == "model:train":
            return lambda: train_model(args.model_name, args.model_path, args.base)
        elif args.command == "model:evaluate":
            return lambda: evaluate_model(args.model_name, args.model_path)
        elif args.command == "model:quantize":
            return lambda: quantize_model(args.model_name, args.model_path, args.new_path)
        else:
            print("Invalid command. Use --help for usage information.")
            print(e)