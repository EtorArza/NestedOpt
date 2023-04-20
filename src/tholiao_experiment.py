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
    from NestedOptimization import experimentProgressTracker
    ref = time.time()
    m_start = 0
    m_end = 180 # in total there are 540 for 60 seeds


    progress_filename = "tholiao_progress.txt"
    start_index = 0
    prog = experimentProgressTracker(progress_filename, start_index, m_end)

    while not prog.done:
        i = prog.get_next_index()
        ref_current = time.time()

        exit_status = os.system(f"python src/tholiao_experiment.py --local_launch {i}")
        os.system("rm other_repos/tholiao/logs/*.npy -f")
        os.system("rm V-REP_PRO_EDU_V3_6_2_Ubuntu18_04/logs/models/20* -f")
        if exit_status == 0:
            prog.mark_index_done(i)
        else:
            print(exit_status)
            exit(1)
