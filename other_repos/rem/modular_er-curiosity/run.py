#!/usr/bin/env python

"""
Experiment runner
"""
from deap import base
from modular_er import ea
from modular_er.history import History
from modular_er.profiler import Profiler
from termcolor import cprint
import argparse
import configparser
import json
import numpy
import os.path
import pickle
import random
import sys
import zipfile


def _write_result(result, path, subfolder=''):
    """Helper method to write data to disk"""
    path = os.path.join(path, subfolder)
    if path and not os.path.exists(path):
        os.makedirs(path)
    for key, item in result.items():
        name = os.path.join(path, '{!s}.pickle'.format(key))
        with open(name, 'wb') as fil:
            pickle.dump(item, fil)


def _checkpoint(generation, evals, result, path, seed, store_freq=-1, profiler=None):
    """Checkpointing function"""
    if store_freq > 0 and generation % store_freq == 0:
        ckpt_name = 'checkpoint_{:d}_{:d}'.format(generation, evals)
        subfolder = os.path.join(str(seed), ckpt_name)
        if profiler is not None:
            result['profile'] = profiler.traces()
        _write_result(result, path, subfolder)


def _load_initial(fil, match=""):
    """Load initial population from file"""
    # Check if the load stems from a zip archive
    if os.path.splitext(fil)[-1] == '.zip':
        with zipfile.ZipFile(fil, 'r') as archive:
            pops = [f for f in archive.namelist()
                    if f.endswith('population.pickle')
                       and match in f]
            full = [f for f in pops if 'checkpoint' not in f]
            ckpts = [f for f in pops if 'checkpoint' in f]
            if full:
                return pickle.loads(archive.read(full[0]))
            else:
                cprint("Using checkpoint to restore population", 'yellow')
                return pickle.loads(archive.read(ckpts[0]))
    else:
        # If not a zip archive we assume it is a pickle file and try to load
        with open(fil, 'rb') as population:
            return pickle.load(population)


if __name__ == '__main__':
    # Create command line parser and options
    parser = argparse.ArgumentParser(description="Experiment runner")
    parser.add_argument('--quiet', '-q', action='store_true',
                        help="Do not print output")
    parser.add_argument('--file', type=argparse.FileType(), default='configs/single.cfg',
                        help="Experiment configuration to execute")
    parser.add_argument('--shared', default="configs/shared.cfg",
                        help="Shared configuration for all experiments")
    parser.add_argument('--seed', type=int, default=1234,
                        help="Seed for the given run")
    parser.add_argument('--output', default=None,
                        help="Output path to store results")
    parser.add_argument('--population', default=None,
                        help="Seed population from a previous run to initialize with")
    parser.add_argument('--parallel', choices=['mpi', 'thread'], default=None,
                        help="Enable parallel execution")
    parser.add_argument('--processes', type=int, default=None,
                        help="Number of processes to use")
    parser.add_argument('--chunksize', type=int, default=1,
                        help="Chunksize for parallelization")
    # Parse arguments and execute experiment
    args = parser.parse_args()
    # Parse configuration file
    config = configparser.ConfigParser()
    # First read shared definitions
    if args.shared:
        config.read([args.shared])
    # Then read experiment specific definitions
    # NOTE: the later can override the former
    config.read_file(args.file)
    # Ensure that 'quiet' is present if not already in config
    if 'quiet' not in config['experiment']:
        config['experiment']['quiet'] = 'no'
    if args.quiet:
        config['experiment']['quiet'] = 'yes'
    # Command line takes precedence over configuration file
    if args.output is not None:
        config['experiment']['output'] = args.output
    elif 'output' not in config['experiment']:
        # If no path is supplied we use the current directory as path
        config['experiment']['output'] = '.'
    # Store experiment configuration and data in ZIP
    path = config.get('experiment', 'output')
    if path and not os.path.exists(path):
        os.makedirs(path)
    # Write configuration file to archive
    with open(os.path.join(path, 'experiment.ini'), 'w') as cfg_file:
        config.write(cfg_file)
    # Store command line invocation and additional
    with open(os.path.join(path, 'command.json'), 'w') as cmd_file:
        cfg = {}
        cfg['command_line'] = ' '.join(sys.argv)
        cfg['args'] = vars(args)
        del cfg['args']['file']
        json.dump(cfg, cmd_file)
    # Based on configuration run desired experiment
    ea = ea.load(config)
    # Setup DEAP toolbox
    toolbox = base.Toolbox()
    # Setup MPI if desired
    if args.parallel == 'mpi':
        from mpi4py.futures import MPIPoolExecutor
        pool = MPIPoolExecutor(max_workers=args.processes)
        toolbox.register('map', pool.map, chunksize=args.chunksize)
    elif args.parallel == 'thread':
        import multiprocessing
        pool = multiprocessing.Pool(processes=args.processes)
        toolbox.register('map', pool.map, chunksize=args.chunksize)
    # If initial population is None, we try to load the population for seeding
    # of the run
    if args.population is not None:
        # If given a zip with multiple seeds inside we assume the users wants
        # to restart with the same seed
        args.population = _load_initial(args.population, str(args.seed))
    # Run actual evolution taking care to set seed
    seed = args.seed
    # Setup random state
    numpy.random.seed(seed)
    random.seed(seed)
    # Setup profiler
    profiler = Profiler()
    toolbox.register('profile', profiler)
    # Setup history
    history = History()
    toolbox.register('history', history.update)
    toolbox.register('history_register', history.register)
    # Setup storage function in toolbox
    toolbox.register('checkpoint', _checkpoint, path=path, seed=seed,
                     store_freq=config.getint('experiment', 'checkpoint_frequency'),
                     profiler=profiler)
    # Perform experiment
    result = ea(toolbox, config, args.population)
    if 'blacklist' in config['experiment']:
        for black in config['experiment']['blacklist'].split(','):
            try:
                del result[black.strip()]
            except KeyError:
                pass
    # Explicit write so that results are always stored
    _write_result(result, path, str(seed))
    _write_result({'profile': profiler.traces()}, path, str(seed))
    _write_result({'history': history}, path, str(seed))
