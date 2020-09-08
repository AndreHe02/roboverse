import numpy as np
import pybullet as p
import gym
import numpy as np
import roboverse.bullet as bullet
import os
from tqdm import tqdm
import argparse
import time
from roboverse.envs.widow250 import Widow250Env

# =========================================================
# Index corresponds to POSITION, ORIENTATION, BUTTTON etc
POSITION = 1
ORIENTATION = 2
ANALOG = 3
BUTTONS = 6
OBJECT_NAME = "lego"
num_timesteps = 35
# =========================================================


def collect_one_trajectory(env):

    prev_vr_theta = 0

    def get_gripper_input(e):
        # Detect change in button, and change trigger state
        if e[BUTTONS][33] & p.VR_BUTTON_IS_DOWN:
            trigger = -0.8
        elif e[BUTTONS][33] & p.VR_BUTTON_WAS_RELEASED:
            trigger = 0.8
        else:
            trigger = 0
        return trigger

    # get VR controller output at one timestamp
    def get_vr_output():
        global trigger
        nonlocal prev_vr_theta
        ee_pos, ee_theta = bullet.get_link_state(
            env.robot_id, env.end_effector_index)
        events = p.getVREvents()

        # detect input from controllers
        assert events, "no input from controller!"
        e = events[0]

        # obtain gripper state from controller trigger
        trigger = get_gripper_input(e)

        # pass controller position and orientation into the environment
        cont_pos = e[POSITION]
        cont_orient = bullet.deg_to_quat([180, 0, 0])
        if ORIENTATION_ENABLED:
            cont_orient = e[ORIENTATION]
            cont_orient = bullet.quat_to_deg(list(cont_orient))

        action = [cont_pos[0] - ee_pos[0],
                  cont_pos[1] - ee_pos[1],
                  cont_pos[2] - ee_pos[2]]
        action = np.array(action) / 2

        grip = trigger
        for _ in range(2):
            action = np.append(action, 0)

        action = np.append(action, cont_orient[2] - prev_vr_theta)
        action = np.append(action, grip)

        # ===========================================================
        # TODO: Add noise during actual data collection
        #noise = 0.1
        #noise_scalings = [noise] * 3 + [0.1 * noise] * 3 + [noise]
        #action += np.random.normal(scale=noise_scalings)
        # ===========================================================

        action = np.clip(action, -1 + EPSILON, 1 - EPSILON)
        prev_vr_theta = cont_orient[2]
        return action

    o = env.reset()
    time.sleep(1.5)
    images = []
    accept = False
    traj = dict(
        observations=[],
        actions=[],
        rewards=[],
        next_observations=[],
        terminals=[],
        agent_infos=[],
        env_infos=[],
        original_object_positions=env.original_object_positions,
    )

    # Collect a fixed length of trajectory
    for i in range(num_timesteps):
        action = get_vr_output()
        print("action: ", action)
        observation = env.get_observation()
        traj["observations"].append(observation)
        next_state, reward, done, info = env.step(action)
        traj["next_observations"].append(next_state)
        traj["actions"].append(action)
        traj["rewards"].append(reward)
        traj["terminals"].append(done)
        traj["agent_infos"].append(info)
        traj["env_infos"].append(info)
        time.sleep(0.03)


    # ===========================================================
    # TODO: Add accepting condition based on reward
    if True: #reward > 0:
        accept = "y"
    # ===========================================================

    return accept, images, traj


if __name__ == "__main__":
    trigger = 0.8
    ORIENTATION_ENABLED = True
    data = []
    EPSILON = 0.005

    env = Widow250Env(gui=True, use_vr=True, control_mode='discrete_gripper')
    env.reset()

    for j in tqdm(range(10)):
        success, images, traj = collect_one_trajectory(env)
        while success != 'y' and success != 'Y':
            print("failed for trajectory {}, collect again".format(j))
            success, images, traj = collect_one_trajectory(env)
        data.append(traj)
    path = os.path.join(__file__, "../..", "vr_demos_success_test.npy")
    np.save(path, data)