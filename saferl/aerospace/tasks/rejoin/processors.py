import gym.spaces
import numpy as np
import math

from scipy.spatial.transform import Rotation

from saferl.environment.tasks.processor import ObservationProcessor, RewardProcessor, StatusProcessor
from saferl.environment.models.geometry import distance


class DubinsObservationProcessor(ObservationProcessor):
    def __init__(self, config):
        super().__init__(config=config)

        # Initialize member variables from config
        self.lead = self.config["lead"]
        self.wingman = self.config["wingman"]
        self.rejoin_region = self.config["rejoin_region"]
        self.reference = self.config["reference"]
        self.mode = self.config["mode"]

        if self.mode == 'rect':
            self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(8,))
            self.obs_norm_const = np.array([10000, 10000, 10000, 10000, 100, 100, 100, 100], dtype=np.float64)
        elif self.mode == 'magnorm':
            self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(12,))
            self.obs_norm_const = np.array([10000, 1, 1, 10000, 1, 1, 100, 1, 1, 100, 1, 1], dtype=np.float64)

    def vec2magnorm(self, vec):
        norm = np.linalg.norm(vec)
        mag_norm_vec = np.concatenate(([norm], vec / norm))
        return mag_norm_vec

    def _process(self, env_objs, status):
        wingman_lead_r = env_objs[self.lead].position - env_objs[self.wingman].position
        wingman_rejoin_r = env_objs[self.rejoin_region].position - env_objs[self.wingman].position

        wingman_vel = env_objs[self.wingman].velocity
        lead_vel = env_objs[self.lead].velocity

        reference_rotation = Rotation.from_quat([0, 0, 0, 1])
        if self.reference == 'wingman':
            reference_rotation = env_objs[self.wingman].orientation.inv()

        wingman_lead_r = reference_rotation.apply(wingman_lead_r)
        wingman_rejoin_r = reference_rotation.apply(wingman_rejoin_r)

        wingman_vel = reference_rotation.apply(wingman_vel)
        lead_vel = reference_rotation.apply(lead_vel)

        if self.mode == 'magnorm':
            wingman_lead_r = self.vec2magnorm(wingman_lead_r)
            wingman_rejoin_r = self.vec2magnorm(wingman_rejoin_r)

            wingman_vel = self.vec2magnorm(wingman_vel)
            lead_vel = self.vec2magnorm(lead_vel)

        obs = np.concatenate([
            wingman_lead_r,
            wingman_rejoin_r,
            wingman_vel,
            lead_vel
        ])

        # normalize observation
        obs = np.divide(obs, self.obs_norm_const)

        obs = np.clip(obs, -1, 1)

        return obs


class Dubins3dObservationProcessor(ObservationProcessor):
    def __init__(self, config):
        super().__init__(config=config)

        # Initialize member variables from config
        self.lead = self.config["lead"]
        self.wingman = self.config["wingman"]
        self.rejoin_region = self.config["rejoin_region"]
        self.reference = self.config["reference"]
        self.mode = self.config["mode"]

        if self.mode == 'rect':
            self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(14,))
            self.obs_norm_const = np.array([10000, 10000, 10000, 10000, 10000, 10000, 100, 100, 100, 100, 100, 100, math.pi, math.pi], dtype=np.float64)
        elif self.mode == 'magnorm':
            self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(18,))
            self.obs_norm_const = np.array([10000, 1, 1, 1, 10000, 1, 1, 1, 100, 1, 1, 1, 100, 1, 1, 1, math.pi, math.pi], dtype=np.float64)

    def generate_observation(self, env_objs):
        def vec2magnorm(vec):
            norm = np.linalg.norm(vec)
            mag_norm_vec = np.concatenate(([norm], vec / norm))
            return mag_norm_vec

        wingman_lead_r = env_objs[self.lead].position - env_objs[self.wingman].position
        wingman_rejoin_r = env_objs[self.rejoin_region].position - env_objs[self.wingman].position

        wingman_vel = env_objs[self.wingman].velocity
        lead_vel = env_objs[self.lead].velocity

        reference_rotation = Rotation.from_quat([0, 0, 0, 1])
        if self.reference == 'wingman':
            reference_rotation = env_objs[self.wingman].orientation.inv()

        wingman_lead_r = reference_rotation.apply(wingman_lead_r)
        wingman_rejoin_r = reference_rotation.apply(wingman_rejoin_r)

        wingman_vel = reference_rotation.apply(wingman_vel)
        lead_vel = reference_rotation.apply(lead_vel)

        if self.mode == 'magnorm':
            wingman_lead_r = vec2magnorm(wingman_lead_r)
            wingman_rejoin_r = vec2magnorm(wingman_rejoin_r)

            wingman_vel = vec2magnorm(wingman_vel)
            lead_vel = vec2magnorm(lead_vel)

        # gamma and roll for 3d orientation info
        roll = np.array([env_objs["wingman"].roll], dtype=np.float64)
        gamma = np.array([env_objs["wingman"].gamma], dtype=np.float64)

        obs = np.concatenate([
            wingman_lead_r,
            wingman_rejoin_r,
            wingman_vel,
            lead_vel,
            roll,
            gamma
        ])

        # normalize observation
        obs = np.divide(obs, self.obs_norm_const)

        obs = np.clip(obs, -1, 1)

        return obs


class RejoinRewardProcessor(RewardProcessor):
    def __init__(self, config):
        super().__init__(config=config)

        # Initialize member variables from config
        self.rejoin_status = self.config["rejoin_status"]
        self.rejoin_prev_status = self.config["rejoin_prev_status"]

    def reset(self, env_objs, status):
        super().reset(env_objs=env_objs, status=status)
        self.step_size = 0
        self.in_rejoin_for_step = False
        self.left_rejoin = False

    def _increment(self, env_objs, step_size, status):
        # Update state variables
        self.left_rejoin = False
        self.in_rejoin_for_step = False
        self.step_size = step_size

        in_rejoin = status[self.rejoin_status]
        in_rejoin_prev = status[self.rejoin_prev_status]
        if in_rejoin and in_rejoin_prev:
            # determine if agent was in rejoin for duration of timestep
            self.in_rejoin_for_step = True
        elif not in_rejoin and in_rejoin_prev:
            # if rejoin region is left, refund all accumulated rejoin reward
            #   this is to ensure that the agent doesn't infinitely enter and leave rejoin region
            self.left_rejoin = True

    def _process(self, env_objs, status):
        # process state variables and return appropriate reward
        step_reward = 0
        if self.in_rejoin_for_step:
            step_reward = self.reward * self.step_size
        elif self.left_rejoin:
            step_reward = -1 * self.total_value
        return step_reward


class RejoinFirstTimeRewardProcessor(RewardProcessor):
    def __init__(self, config):
        super().__init__(config=config)

        # Initialize member variables from config
        self.rejoin_status = self.config["rejoin_status"]

    def reset(self, env_objs, status):
        super().reset(env_objs=env_objs, status=status)
        self.rejoin_first_time = False
        self.rejoin_first_time_applied = False
        self.in_rejoin = status[self.rejoin_status]

    def _increment(self, env_objs, step_size, status):
        # return step_value of reward accumulated during interval of size timestep
        if self.rejoin_first_time:
            # if first time flag true, first time reward has already been applied
            self.rejoin_first_time_applied = True
            self.rejoin_first_time = False

        in_rejoin = status[self.rejoin_status]
        if in_rejoin and not self.rejoin_first_time_applied:
            # if in rejoin and first time reward not already applied, it is the agent's first timestep in rejoin region
            self.rejoin_first_time = True

    def _process(self, env_objs, status):
        # process state variables and return appropriate reward
        step_reward = 0
        if self.rejoin_first_time:
            step_reward = self.reward
        return step_reward


class RejoinDistanceChangeRewardProcessor(RewardProcessor):
    def __init__(self, config):
        super().__init__(config=config)

        # Initialize member variables from config
        self.rejoin_status = self.config["rejoin_status"]
        self.wingman = self.config["wingman"]
        self.rejoin_region = self.config["rejoin_region"]

    def reset(self, env_objs, status):
        super().reset(env_objs=env_objs, status=status)
        self.prev_distance = distance(env_objs[self.wingman], env_objs[self.rejoin_region])
        self.cur_distance = self.prev_distance
        self.in_rejoin = status[self.rejoin_status]

    def _increment(self, env_objs, step_size, status):
        # Update state variables
        self.prev_distance = self.cur_distance
        self.cur_distance = distance(env_objs[self.wingman], env_objs[self.rejoin_region])
        self.in_rejoin = status[self.rejoin_status]

    def _process(self, env_objs, status):
        # process state and return appropriate step reward
        step_reward = 0
        distance_change = self.cur_distance - self.prev_distance
        if not self.in_rejoin:
            step_reward = distance_change * self.reward
        return step_reward


class DubinsInRejoin(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.wingman = self.config["wingman"]
        self.rejoin_region = self.config["rejoin_region"]

    def reset(self, env_objs, status):
        ...

    def _increment(self, env_objs, step_size, status):
        # this status comes from first principles of the environment and therefore does not require a state machine
        ...

    def _process(self, env_objs, status):
        # return the current status
        in_rejoin = env_objs[self.rejoin_region].contains(env_objs[self.wingman])
        return in_rejoin


class DubinsInRejoinPrev(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.rejoin_status = self.config["rejoin_status"]

    def reset(self, env_objs, status):
        self.in_rejoin_prev = False
        self.in_rejoin_current = status[self.rejoin_status]

    def _increment(self, env_objs, step_size, status):
        # update rejoin region state variables
        self.in_rejoin_prev = self.in_rejoin_current
        self.in_rejoin_current = status[self.rejoin_status]

    def _process(self, env_objs, status):
        # return the previous rejoin status
        return self.in_rejoin_prev


class DubinsRejoinTime(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.rejoin_status = self.config["rejoin_status"]

    def reset(self, env_objs, status):
        self.rejoin_time = 0
        self.in_rejoin = status[self.rejoin_status]

    def _increment(self, env_objs, step_size, status):
        # update state
        self.in_rejoin = status[self.rejoin_status]
        if self.in_rejoin:
            self.rejoin_time += step_size
        else:
            self.rejoin_time = 0

    def _process(self, env_objs, status):
        # return the current status
        return self.rejoin_time


class DubinsTimeElapsed(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)

    def reset(self, env_objs, status):
        self.time_elapsed = 0

    def _increment(self, env_objs, step_size, status):
        # update status
        self.time_elapsed += step_size

    def _process(self, env_objs, status):
        # return the current status
        return self.time_elapsed


class DubinsLeadDistance(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.wingman = self.config["wingman"]
        self.lead = self.config["lead"]

    def reset(self, env_objs, status):
        ...

    def _increment(self, env_objs, step_size, status):
        # this status comes from first principles of the environment and therefore does not require a state machine
        ...

    def _process(self, env_objs, status):
        # return the current status
        lead_distance = distance(env_objs[self.wingman], env_objs[self.lead])
        return lead_distance


class DubinsFailureStatus(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.lead_distance_key = self.config["lead_distance"]
        self.time_elapsed_key = self.config["time_elapsed"]
        self.safety_margin = self.config['safety_margin']
        self.timeout = self.config['timeout']
        self.max_goal_dist = self.config['max_goal_distance']

    def reset(self, env_objs, status):
        # reset state
        self.lead_distance = status[self.lead_distance_key]
        self.time_elapsed = status[self.time_elapsed_key]

    def _increment(self, env_objs, step_size, status):
        # update state
        self.lead_distance = status[self.lead_distance_key]
        self.time_elapsed = status[self.time_elapsed_key]

    def _process(self, env_objs, status):
        # process current state variables and return failure status
        failure = False
        if self.lead_distance < self.safety_margin['aircraft']:
            failure = 'crash'
        elif self.time_elapsed > self.timeout:
            failure = 'timeout'
        elif self.lead_distance >= self.max_goal_dist:
            failure = 'distance'

        return failure


class DubinsSuccessStatus(StatusProcessor):
    def __init__(self, config):
        super().__init__(config=config)
        # Initialize member variables from config
        self.rejoin_time_key = self.config["rejoin_time"]
        self.success_time = self.config["success_time"]

    def reset(self, env_objs, status):
        # reset state
        self.rejoin_time = status[self.rejoin_time_key]

    def _increment(self, env_objs, timestep, status):
        # update state
        self.rejoin_time = status[self.rejoin_time_key]

    def _process(self, env_objs, status):
        # process state and return new status
        success = False
        if self.rejoin_time > self.success_time:
            success = True
        return success
