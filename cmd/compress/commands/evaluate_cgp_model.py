import os
import pandas as pd
import seaborn as sns
import commands.datastore as store
import experiments.manager as experiments
from pathlib import Path
from experiments.single_channel.experiment import SingleChannelExperiment
from parse import parse
from commands.factory.experiment import create_all_experiment, create_experiment
from tqdm import tqdm
from functools import partial

def evaluate_cgp_model(args):
    for experiment in create_all_experiment(args):
        experiment.config.set_start_run(args.start_run)
        experiment.config.set_start_generation(args.start_generation)
        experiment = experiment.get_result_eval_env()
        experiment.get_model_metrics_from_statistics()

def sample(top: int, f: str):
    df = pd.read_csv(f)
    return pd.concat([df.tail(n=1), df.sample(n=top-1)])

def evaluate_model_metrics(args):
    experiment_list = args.experiment
    experiment = create_experiment(args, prepare=False)
    data_store = store.Datastore()
    data_store.init_experiment_path(experiment)
    df_factory = pd.read_csv if args.top is None else partial(sample, args.top)

    if not isinstance(experiment, experiments.MultiExperiment):
        experiment_list = [experiment]

    for case in experiment_list:
        x = experiment.get_experiment(case, from_filesystem = True) if isinstance(experiment, experiments.MultiExperiment) else experiment
        
        for run in (args.runs or x.get_infered_weights_run_list()):
            df = pd.concat([df_factory(file) for file in x.get_train_statistics(runs=run)])

            df.drop(columns="depth", inplace=True, errors="ignore")
            df = df[~(
                df["error"].duplicated() & df["quantized_energy"].duplicated() & 
                df["energy"].duplicated() & df["quantized_delay"].duplicated() & 
                df["delay"].duplicated() & df["area"].duplicated() &
                df["gate_count"].duplicated() & df["chromosome"].duplicated())]   

            df = df.loc[~df["chromosome"].isna(), :].copy()
            df["Top-1"] = None
            df["Top-5"] = None
            df["Loss"] = None        
            
            chromosomes_file = data_store.derive_from_experiment(x) / "chromosomes.txt"
            stats_file = data_store.derive_from_experiment(x) / f"eval_statistics.{run}.csv"
            weights_file = data_store.derive_from_experiment(x) / "all_weights" / (f"weights.{run}." + "{run}.txt")
            weights_file.unlink(missing_ok=True)
            
            weights_file.parent.mkdir(exist_ok=True, parents=True)
            
            with open(chromosomes_file, "w") as f:
                for _, row in df.iterrows():
                    f.write(row["chromosome"] + "\n")
            
            x.evaluate_chromosomes(chromosomes_file, stats_file, weights_file)        
            
            def weight_iterator():
                for f in os.listdir(weights_file.parent):
                    yield x.get_weights(weights_file.parent / f)
            
            cached_top_k, cached_loss = None, None
            top_1 = []; top_5 = []; losses = []
            fitness_values = ["error", "quantized_energy", "energy", "area", "quantized_delay", "delay", "depth", "gate_count", "chromosome"]
            with tqdm(zip(weight_iterator(), df.iterrows(), pd.read_csv(stats_file).iterrows()), unit="Record", total=len(df.index), leave=True) as records:
                for (weights, plans), (index, row), (eval_index, eval_row) in records:
                    df.loc[index, fitness_values] = eval_row[fitness_values]
                    print("start error:", row["error"], "new error:", eval_row["error"])  
                    if eval_row["error"] == 0:
                        if cached_top_k is None:
                            cached_top_k, cached_loss = x.get_reference_model_metrics(cache=False, batch_size=None, top=[1, 5])
                        top_1.append(cached_top_k[1])
                        top_5.append(cached_top_k[5])
                        losses.append(cached_loss)
                    else:          
                        print("error:", eval_row["error"])   
                        if eval_row["error"] == 0:
                            top_1.append(cached_top_k[1])
                            top_5.append(cached_top_k[5])
                            losses.append(cached_loss)
                        else:
                            model = x._model_adapter.inject_weights(weights, plans)
                            top_k, loss = model.evaluate(top=[1, 5], batch_size=None)
                            top_1.append(top_k[1])
                            top_5.append(top_k[5])
                            losses.append(loss)
            df["Top-1"] = top_1
            df["Top-5"] = top_5
            df["Loss"] = losses
            destination = data_store.derive_from_experiment(experiment) / "model_metrics" / (x.get_name(depth=1) + f".{run}.csv")
            destination.parent.mkdir(exist_ok=True, parents=True)                                                                                             
            df.to_csv(destination, index=False)