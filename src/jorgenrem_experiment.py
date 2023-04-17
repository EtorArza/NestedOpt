import sys
import os



def launch_one(experiment_index):
    from NestedOptimization import Parameters, NestedOptimization
    previousDir = os.getcwd()
    os.chdir("other_repos/jorgenrem")
    params = Parameters("jorgenrem", experiment_index)
    no = NestedOptimization("../../results/jorgenrem/data", params)
    params.print_parameters()
    sys.path.append(sys.path[0]+"/../other_repos/jorgenrem/")
    from run import main
    sys.argv = [sys.argv[0]]
    main(no)
    os.chdir(previousDir)


def launch_one_parameter_tuning(seed, default_inner_quantity):
    from NestedOptimization import Parameters, NestedOptimization
    previousDir = os.getcwd()
    os.chdir("other_repos/jorgenrem")
    params = Parameters("jorgenrem", 1)
    params.seed = seed
    def return_filename():
        return f"paramtuning_{default_inner_quantity}_{seed}"
    params.get_result_file_name=return_filename
    params._default_inner_quantity = default_inner_quantity
    params._inner_quantity_proportion = 1.0 
    params._inner_length_proportion = 1.0

    params.print_parameters()
    no = NestedOptimization("../../results/jorgenrem/data", params, deletePreviousResults=True)
    sys.path.append(sys.path[0]+"/../other_repos/jorgenrem/")
    print(sys.path)
    from run import main
    import modular_er.eval
    modular_er.eval.save_data_animation = lambda dump_path, video_label, individual, controller, no, seconds, max_size, warmup, env: None
    sys.argv = [sys.argv[0]]
    main(no)
    os.chdir(previousDir)



if sys.argv[1] == "--local_launch":
    import itertools
    import time
    launch_one(int(sys.argv[2]))

if sys.argv[1] == "--local_launch_tuning":
    import itertools
    import time
    assert len(sys.argv) == 4
    launch_one_parameter_tuning(int(sys.argv[2]), int(sys.argv[3]))

elif sys.argv[1] == "--visualize":
    from NestedOptimization import Parameters, NestedOptimization

    params = Parameters("jorgenrem", int(sys.argv[2]))
    params.print_parameters()

    no = NestedOptimization("../../results/jorgenrem/data", params)
    sys.path.append(sys.path[0]+"/../other_repos/jorgenrem/")
    print(sys.path)
    from modular_er.eval import animate_from_dump


    animate_from_dump(f"other_repos/jorgenrem/dumps_for_animation/animation_dump_current{int(sys.argv[2])}.wb")
    animate_from_dump(f"other_repos/jorgenrem/dumps_for_animation/animation_dump_best{int(sys.argv[2])}.wb")

elif sys.argv[1] == "--tune":
    seeds = list(range(20))
    from itertools import product
    from NestedOptimization import convert_from_seconds, experimentProgressTracker
    import joblib
    import pandas as pd
    import time

    parameter_combs = list(product(seeds, [1, 8, 32, 128, 512]))
    progress_filename = "jorgenremtune_progress_report.txt"
    start_index = 0
    prog = experimentProgressTracker(progress_filename, start_index, len(parameter_combs))
    while not prog.done:
        i = prog.get_next_index()
        seed, default_inner_quantity = parameter_combs[i]
        print("seed, default_inner_quantity = ", seed, default_inner_quantity)
        exit_status = os.system(f"python src/jorgenrem_experiment.py --local_launch_tuning {seed} {default_inner_quantity}")
        if exit_status == 0:
            prog.mark_index_done(i)
        else:
            print(exit_status)
            exit(1)



elif sys.argv[1] == "--plot_tune":
    import os
    import pandas as pd
    import numpy as np
    from matplotlib import pyplot as plt

    def find_between(s, start, end): # find substring between two strings
        return (s.split(start))[1].split(end)[0]

    exp_dir = "results/gymrem2d/data"

    rows = []
    for csv_name in os.listdir(exp_dir):
        if ".txt" in csv_name and "paramtuning" in csv_name:
            df = pd.read_csv(exp_dir + "/" + csv_name)
            f = df.query("level == 2")["f_best"].iloc[-1]
            step = df.query("level == 2")["step"].iloc[-1]
            nrows = df.query("level == 2").shape[0]
            innerquantity = int(find_between(csv_name, "paramtuning_","_"))
            seed = int(find_between(csv_name, "_",".txt"))
            rows.append([innerquantity, seed, f, nrows, step])
    df = pd.DataFrame(rows, columns=["innerquantity", "seed", "f", "nrows","step"])

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    inner_quantity_list = sorted(df["innerquantity"].unique())
    print("inner_quantity_list =", inner_quantity_list)

    # # https://stackoverflow.com/questions/43345599/process-pandas-dataframe-into-violinplot
    # fig, axes = plt.subplots()
    # axes.violinplot(dataset = [df[df.innerquantity == el]["f"].values for el in inner_quantity_list],showmedians=True)
    # axes.set_title('Day Ahead Market')
    # axes.yaxis.grid(True)
    # axes.set_xlabel('Scenario')
    # axes.set_ylabel('LMP ($/MWh)')
    # plt.show()
    # plt.close()

    def set_axis_style(ax, labels):
        ax.set_xticks(np.arange(1, len(labels) + 1), labels=labels)
        ax.set_xlim(0.25, len(labels) + 0.75)
        ax.set_xlabel('Controllers evaluated per morphology')

    plt.violinplot(dataset = [df[df.innerquantity == el]["f"].values for el in inner_quantity_list],showmedians=True)
    set_axis_style(plt.gca(), [str(el) for el in inner_quantity_list])
    plt.title("f")
    plt.show()
    plt.close()

    plt.violinplot(dataset = [df[df.innerquantity == el]["nrows"].values for el in inner_quantity_list],showmedians=True)
    set_axis_style(plt.gca(), [str(el) for el in inner_quantity_list])
    plt.title("nrows")
    plt.show()
    plt.close()

    plt.violinplot(dataset = [df[df.innerquantity == el]["step"].values for el in inner_quantity_list],showmedians=True)
    set_axis_style(plt.gca(), [str(el) for el in inner_quantity_list])
    plt.title("step")
    plt.yscale("log")
    plt.show()
    plt.close()

else:
    raise ValueError(f"Argument {sys.argv[1]} not recognized.")