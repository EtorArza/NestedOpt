from argparse import ArgumentError

import subprocess
import time
import re
from os.path import exists
import os
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from tqdm import tqdm as tqdm
from joblib import Parallel, delayed
import argparse



def launch_one(experiment_index):
    from NestedOptimization import Parameters, NestedOptimization

    params = Parameters("gymrem2d", experiment_index)
    params.print_parameters()
    no = NestedOptimization("../../../results/gymrem2d/data", params)
    sys.path.append(sys.path[0]+"/../other_repos/gymrem2d/ModularER_2D/")
    print(sys.path)
    import REM2D_main
    from REM2D_main import setup, run2D
    config, dir = setup(no)
    experiment = run2D(no,config,dir)
    experiment.run(config)


def launch_one_parameter_tuning(seed, default_inner_quantity):
    from NestedOptimization import Parameters, NestedOptimization
    params = Parameters("gymrem2d", 1)
    params.seed = seed
    def return_filename():
        return f"paramtuning_{default_inner_quantity}_{seed}"
    params.get_result_file_name=return_filename
    params._default_inner_quantity = default_inner_quantity
    params._default_inner_length = 100
    params._inner_quantity_proportion = 1.0 
    params._inner_length_proportion = 1.0

    params.print_parameters()
    no = NestedOptimization("../../../results/gymrem2d/data", params)
    sys.path.append(sys.path[0]+"/../other_repos/gymrem2d/ModularER_2D/")
    print(sys.path)
    import REM2D_main
    from REM2D_main import setup, run2D
    REM2D_main.save_data_animation = lambda dump_path, no, ind, tree_dpth, video_label: None
    

    config, dir = setup(no)
    experiment = run2D(no,config,dir)
    experiment.run(config)



if sys.argv[1] == "--local_launch":
    import itertools
    import time
    launch_one(int(sys.argv[2]))


elif sys.argv[1] == "--visualize":
    from NestedOptimization import Parameters, NestedOptimization

    params = Parameters("gymrem2d", int(sys.argv[2]))
    params.print_parameters()

    no = NestedOptimization("../../../results/gymrem2d/data", params)
    sys.path.append(sys.path[0]+"/../other_repos/gymrem2d/ModularER_2D/")
    print(sys.path)
    import REM2D_main
    from REM2D_main import animate_from_dump

    animate_from_dump(f"other_repos/gymrem2d/dumps_for_animation/animation_dump_current{int(sys.argv[2])}.wb")
    animate_from_dump(f"other_repos/gymrem2d/dumps_for_animation/animation_dump_best{int(sys.argv[2])}.wb")

elif sys.argv[1] == "--tune":
    seeds = list(range(20))
    from itertools import product
    from NestedOptimization import convert_from_seconds
    import joblib

    parameter_combs = list(product(seeds, [20, 80, 320, 1280]))
    n = len(parameter_combs)
    ref = time.time()

    with open("tholiao_progress_report.txt","w") as f:
        f.write("start.\n")


    def launch_one_tune(i):
        seed,default_inner_quantity = parameter_combs[i]
        print("COMBS",seed,default_inner_quantity)
        orig_cwd = os.getcwd()
        print("original CWD:", orig_cwd)
        try:
            launch_one_parameter_tuning(seed, default_inner_quantity)
        except SystemExit:
            pass
        os.chdir(orig_cwd)

        elapsed_time = time.time() - ref
        time_left = elapsed_time / (i+1) * n - elapsed_time
        with open("gymrem2d_progress_report.txt","a") as f:
            f.write(f"{i/n}, {convert_from_seconds(time_left)} | {i}, {convert_from_seconds(elapsed_time)}\n")

    for i in range(n):
        launch_one_tune(i)


elif sys.argv[1] == "--plot_tune":
    import os
    import pandas as pd
    import numpy as np

    exp_dir = "results/gymrem2d/data"

    for csv_name in tqdm(os.listdir(exp_dir)):
        if ".txt" in csv_name and "paramtuning" in csv_name:
         df = pd.read_csv(exp_dir + "/" + csv_name)
         print(df)
         exit(0)

else:
    raise ValueError(f"Argument {sys.argv[1]} not recognized.")