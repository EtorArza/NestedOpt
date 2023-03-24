import sys
import os
import time




def local_launch_one(experiment_index):

    os.chdir("other_repos/tholiao")
    sys.path.append(sys.path[0]+"/../other_repos/tholiao")
    sys.path.append("/home/paran/Dropbox/BCAM/08_estancia_2/code/other_repos/tholiao")
    print(sys.path)
    from main import cli_main

    os.system("rm -f logs/params.npy")
    os.system("killall -9 vrep.sh")
    os.system("killall -9 vrep")
    time.sleep(5)
    # https://aweirdimagination.net/2020/06/28/kill-child-jobs-on-script-exit/
    os.system("cd ../../V-REP_PRO_EDU_V3_6_2_Ubuntu18_04/ &&  ./vrep.sh -h &")
    time.sleep(5)


    from NestedOptimization import Parameters, NestedOptimization

    params = Parameters("tholiao", experiment_index)
    params.print_parameters()

    import random
    import numpy as np
    random.seed(params.seed)
    np.random.seed(params.seed)
 
    no = NestedOptimization("../../results/tholiao/data/", params)



    cli_main(no)


if sys.argv[1] == "--local_launch":
    experiment_index = int(sys.argv[2])
    sys.argv = sys.argv[:1]
    local_launch_one(experiment_index)


elif sys.argv[1] == "--sequential_launch":
    import time
    from NestedOptimization import convert_from_seconds
    ref = time.time()
    m = 279
    with open("tholiao_progress_report.txt","w") as f:
        f.write("start.\n")
    for i in range(m):
        os.system(f"python src/tholiao_experiment.py --local_launch {i}")
        elapsed_time = time.time() - ref
        time_left = elapsed_time / (i+1) * m - elapsed_time
        with open("tholiao_progress_report.txt","a") as f:
            f.write(f"{i/m}, {convert_from_seconds(time_left)} | {i}, {convert_from_seconds(elapsed_time)}\n")
