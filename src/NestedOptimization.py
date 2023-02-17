import time
from threading import Thread, Lock
import numpy as np

class stopwatch:
    paused=False
    def __init__(self):
        self.reset()

    def reset(self):
        self.start_t = time.time()
        self.pause_t=0
        self.paused=False

    def pause(self):
        self.pause_start = time.time()
        self.paused=True

    def resume(self):
        if self.paused:
            self.pause_t += time.time() - self.pause_start
            self.paused = False

    def get_time(self):
        # print("Pause time = ", self.pause_t)
        # print("Time without pause = ", time.time() - self.start_t)
        # print("Time = ", time.time() - self.start_t - self.pause_t)
        current_extra_pause_time = 0.0
        if self.paused:
            current_extra_pause_time = time.time() - self.pause_start
        return time.time() - self.start_t - self.pause_t - current_extra_pause_time

    def get_time_string_short_format(self):
        return "{:.4f}".format(self.get_time())

class NestedOptimization:

    sw = stopwatch()
    sw_reeval = stopwatch()
    f_observed = float("-inf")
    f_best = float("-inf")
    f_reeval_observed = float("-inf")
    f_reeval_best = float("-inf")
    step = 0
    reevaluating_steps = 0
    iteration = 0
    evaluation = 0
    done = False
    write_header = True
    iterations_since_best_found = 0
    is_reevaluating = False

    result_file_path = None
    experiment_name = None
    mode = None
    inners_per_outer_proportion = None
    inner_length_proportion = None
    max_frames = None

    save_best_visualization_required = False

    SAVE_EVERY = 5
    mutex = Lock()


    def __init__(self, result_file_path, mode, max_frames, inners_per_outer_proportion, inner_length_proportion, experiment_index, experiment_name):
        self.sw_reeval.pause()
        self.result_file_path = result_file_path
        self.mode = mode
        self.max_frames = max_frames
        self.inners_per_outer_proportion = inners_per_outer_proportion
        self.inner_length_proportion = inner_length_proportion
        self.experiment_index = experiment_index
        self.experiment_name = experiment_name
        assert mode in ("saveall", "standard")


    def print_to_result_file(self, msg_string):
        self.mutex.acquire()
        try:
            with open(self.result_file_path, "a") as f:
                    f.write(msg_string)
        finally:
            self.mutex.release()

    def next_step(self):
        if self.is_reevaluating:
            self.reevaluating_steps += 1
        else:
            self.step += 1


    def next_inner(self):
        self.iteration += 1


    def next_outer(self, f_observed):
        assert not f_observed is None
        self.f_observed = f_observed

        if self.step > self.max_frames:
            print("Finished at", self.max_frames,"frames.")
            exit(0)

        self.evaluation += 1
        self.check_if_best(level=2)
        self.write_to_file(level=2)
        print("next_outer()", f_observed, ", progress:", self.step / self.max_frames, ", time left:", self.sw.get_time() / (self.step / self.max_frames) )


    def next_reeval(self, f_reeval_observed):
        self.f_reeval_observed = f_reeval_observed
        self.check_if_best(level=3)
        self.write_to_file(level=3)
        self.is_reevaluating = False
        self.sw_reeval.pause()
        self.sw.resume()
        print("next_reeval()", f_reeval_observed, ", progress:", self.step / self.max_frames, ", time left:", self.sw.get_time() / (self.step / self.max_frames) )


    def check_if_best(self, level):
        # print("Checking for best found.")
        if level == 2:
            if self.f_observed > self.f_best:
                self.f_best = self.f_observed
                self.is_reevaluating = True
                self.sw_reeval.resume()
                self.sw.pause()
                print("best_found! (level 2)")
        if level == 3:
            if self.f_reeval_observed > self.f_reeval_best:
                self.f_reeval_best = self.f_reeval_observed
                self.save_best_visualization_required = True
                print("best_found! (level 3)")



    def write_to_file(self, level):
        self.mutex.acquire()
        try:
            with open(self.result_file_path, "a") as f:
                if self.write_header:
                    f.write("level,evaluation,f_best,f,time,time_including_reeval,step,step_including_reeval\n")
                    self.write_header = False
                if level == 2:
                    f.write(f"{level},{self.evaluation},{self.f_best},{self.f_observed},{self.sw.get_time()},{self.sw.get_time() + self.sw_reeval.get_time()},{self.step},{self.step + self.reevaluating_steps}\n")
                elif level == 3:
                    f.write(f"{level},{self.evaluation},{self.f_reeval_best},{self.f_reeval_observed},{self.sw.get_time()},{self.sw.get_time() + self.sw_reeval.get_time()},{self.step},{self.step + self.reevaluating_steps}\n")
        finally:
            self.mutex.release()

    def get_seed(self):
        return 2
