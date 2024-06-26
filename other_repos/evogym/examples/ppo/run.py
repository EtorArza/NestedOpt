import os, sys
sys.path.insert(1, os.path.join(sys.path[0], 'externals', 'pytorch_a2c_ppo_acktr_gail'))

import numpy as np
import time
from collections import deque
import torch

from ppo import utils
from ppo.arguments import get_args
from ppo.evaluate import evaluate
from ppo.envs import make_vec_envs

from a2c_ppo_acktr import algo
from a2c_ppo_acktr.algo import gail
from a2c_ppo_acktr.model import Policy
from a2c_ppo_acktr.storage import RolloutStorage

import evogym.envs

# Derived from
# https://github.com/ikostrikov/pytorch-a2c-ppo-acktr-gail

def run_ppo(
    structure,  
    saving_convention, 
    env_name,
    no,
    test):

    verbose = False
    if verbose and test:
        print("Reevaluating...")
    assert (structure == None) == (saving_convention == None)

    # if verbose:
    #     print(f'Starting training on \n{structure}\nat {saving_convention}...\n')


    morphology = structure[0]

    # 0 -> Empty
    # 1 -> Black rigid
    # 2 -> Grey flexible
    # 3 -> Orange (controllable)
    # 4 -> Blue (controllable)
    import copy
    best_structure = copy.deepcopy(structure)

    controller_size = np.sum(morphology == 3) + np.sum(morphology == 4)
    controller_size2 = structure[1].shape[1]
    morphology_size = np.sum(morphology != 0)

    args = get_args()

    args.env_name = env_name

    args.num_steps = no.get_inner_length()


    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    if args.cuda and torch.cuda.is_available() and args.cuda_deterministic:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    log_dir = args.log_dir
    if saving_convention != None:
        log_dir = os.path.join(saving_convention[0], log_dir, "robot_" + str(saving_convention[1]))
    eval_log_dir = log_dir + "_eval"
    utils.cleanup_log_dir(log_dir)
    utils.cleanup_log_dir(eval_log_dir)

    torch.set_num_threads(1)
    device = torch.device("cuda:0" if args.cuda else "cpu")

    envs = make_vec_envs(args.env_name, structure, args.seed, args.num_processes,
                         args.gamma, args.log_dir, device, False)

    # import code; code.interact(local=locals()) # start interactive for debugging
    if verbose:
        print("Environment dims -->", envs.observation_space.shape, envs.action_space.shape)


    actor_critic = Policy(
        envs.observation_space.shape,
        envs.action_space,
        base_kwargs={'recurrent': args.recurrent_policy})
    actor_critic.to(device)

    if args.algo == 'a2c' or args.algo == 'acktr':
        print('Warning: this code has only been tested with ppo.')
        exit(1)
    elif args.algo == 'ppo':
        agent = algo.PPO(
            actor_critic,
            args.clip_param,
            args.ppo_epoch,
            args.num_mini_batch,
            args.value_loss_coef,
            args.entropy_coef,
            lr=args.lr,
            eps=args.eps,
            max_grad_norm=args.max_grad_norm)
    # print('args.num_steps', args.num_steps)

    rollouts = RolloutStorage(args.num_steps, args.num_processes,
                              envs.observation_space.shape, envs.action_space,
                              actor_critic.recurrent_hidden_state_size)

    obs = envs.reset()
    rollouts.obs[0].copy_(obs)
    rollouts.to(device)

    episode_rewards = deque(maxlen=10)

    start = time.time()
    num_updates = int(
        args.num_env_steps) // args.num_steps // args.num_processes

    rewards_tracker = []
    avg_rewards_tracker = []
    sliding_window_size = 10
    max_determ_avg_reward = float('-inf')
    # new_step = no.step

    for j in range(num_updates):

        cum_reward = 0
        if args.use_linear_lr_decay:
            # decrease learning rate linearly
            utils.update_linear_schedule(
                agent.optimizer, j, num_updates,
                agent.optimizer.lr if args.algo == "acktr" else args.lr)

        for step in range(args.num_steps):
            # Sample actions
            with torch.no_grad():
                value, action, action_log_prob, recurrent_hidden_states = actor_critic.act(
                    rollouts.obs[step], rollouts.recurrent_hidden_states[step],
                    rollouts.masks[step])

            # Obser reward and next obs
            obs, reward, done, infos = envs.step(action)
            cum_reward += float(reward)

            no.next_step()

            # track rewards
            for info in infos:
                if 'episode' in info.keys():
                    episode_rewards.append(info['episode']['r'])
                    rewards_tracker.append(info['episode']['r'])
                    if len(rewards_tracker) < 10:
                        avg_rewards_tracker.append(np.average(np.array(rewards_tracker)))
                    else:
                        avg_rewards_tracker.append(np.average(np.array(rewards_tracker[-10:])))

            # If done then clean the history of observations.
            masks = torch.FloatTensor(
                [[0.0] if done_ else [1.0] for done_ in done])
            bad_masks = torch.FloatTensor(
                [[0.0] if 'bad_transition' in info.keys() else [1.0]
                 for info in infos])
            rollouts.insert(obs, recurrent_hidden_states, action,
                            action_log_prob, value, reward, masks, bad_masks)

        with torch.no_grad():
            next_value = actor_critic.get_value(
                rollouts.obs[-1], rollouts.recurrent_hidden_states[-1],
                rollouts.masks[-1]).detach()


        rollouts.compute_returns(next_value, args.use_gae, args.gamma,
                                 args.gae_lambda, args.use_proper_time_limits)

        value_loss, action_loss, dist_entropy = agent.update(rollouts)

        rollouts.after_update()
     
        
        # evaluate the controller and save it if it does the best so far
        if (args.eval_interval is not None and len(episode_rewards) > 1
                and j % args.eval_interval == 0):
            
            obs_rms = utils.get_vec_normalize(envs).obs_rms
            # old_step = no.step
            # print("Steps used trainig, ", no.step - new_step)
            determ_avg_reward = evaluate(args.num_evals, actor_critic, obs_rms, args.env_name, structure, args.seed, args.num_processes, eval_log_dir, device, no)
            # print("Steps used on evaluate: ", no.step - old_step)
            # print("Determ_avg_reward - ", no.step, no.iteration, determ_avg_reward)
            # new_step = no.step

            if determ_avg_reward > max_determ_avg_reward:
                max_determ_avg_reward = determ_avg_reward
                best_structure = copy.deepcopy(structure)
                if test or no.params.experiment_mode == "proposedmethod":
                    torch.save([actor_critic,getattr(utils.get_vec_normalize(envs), 'obs_rms', None)], no.controller_path_for_animation)

            no.next_inner(max_determ_avg_reward)

        # return upon reaching the termination condition
        if no.ESNOF_stop or (no.get_inner_quantity() <= j):
            structure = copy.deepcopy(best_structure)
            if not test:
                no.next_outer(max_determ_avg_reward, controller_size, controller_size2, morphology_size)
            elif no.is_reevaluating_flag:
                no.next_reeval(max_determ_avg_reward, controller_size, controller_size2, morphology_size)
            return max_determ_avg_reward
