import pandas as pd
import numpy as np
import jsonlines
# from flatten_json import flatten_json
import time
import pickle
import matplotlib.pyplot as pyplot
import argparse

"""
This script takes in the path to a rejoin task log file and a worker episode number and generates some common positional 
plots using matplotlib.

Author: John McCarroll
5-18-2021
"""

def get_args():
    """
    A function to process script args.

    Returns
    -------
    argparse.Namespace
        Collection of command line arguments and their values
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--log_path', type=str, help="the path to the log file", required=True)
    parser.add_argument('--worker_episode_number', type=int, default=0, help="the identifying number of the episode logged", required=True)
    parser.add_argument('--output', type=str, default="~/", help="the directory in which to save generated plots", required=False)

    return parser.parse_args()


def process_log(path_to_file: str, episode_number: int):
    """
    This function converts the specified episode (if it exists) into a dictionary for ease of plotting.

    Parameters
    ----------
    path_to_file : str
        The location of the log file to be processed.
    episode_number : int
        The identifying number assigned to the episode by a worker.

    Returns
    -------
    episode_dict : dict
        A collection of position data (lists) for environment objects throughout the episode.
    """
    episode_dict = {
        "step_number": [],
        "lead_x": [],
        "lead_y": [],
        "lead_z": [],
        "wingman_x": [],
        "wingman_y": [],
        "wingman_z": [],
        "rejoin_region_x": [],
        "rejoin_region_y": [],
        "rejoin_region_z": [],
    }

    # open log file
    with jsonlines.open(path_to_file, 'r') as log:
        episode_duration = 0
        # iterate through json objects in log
        for state in log:
            # ensure correct episode
            if state["worker_episode_number"] == episode_number:
                # add positional info of state to episode_dict
                episode_dict["ID"] = state["episode_ID"]
                episode_dict["step_number"].append(state["step_number"])

                episode_dict["lead_x"].append(state["info"]["lead"]["x"])
                episode_dict["lead_y"].append(state["info"]["lead"]["y"])

                episode_dict["wingman_x"].append(state["info"]["wingman"]["x"])
                episode_dict["wingman_y"].append(state["info"]["wingman"]["y"])

                episode_dict["rejoin_region_x"].append(state["info"]["rejoin_region"]["x"])
                episode_dict["rejoin_region_y"].append(state["info"]["rejoin_region"]["y"])

                # 3d envs
                if "z" in state["info"]["lead"]:
                    episode_dict["lead_z"].append(state["info"]["lead"]["z"])
                    episode_dict["wingman_z"].append(state["info"]["wingman"]["z"])
                    episode_dict["rejoin_region_z"].append(state["info"]["rejoin_region"]["z"])

    return episode_dict


def plot(x, y, title: str):
    """
    This function is responsible for plotting the provided data to a pyplot Axes. The resulting Figure object is returned.

    Parameters
    ----------
    x : list
        A list of values to plot along the x axes.
    y : list or dict
        A list of values to plot along the y axes
        or a dictionary of lists to plot along the y axes.
    title : str
        The title to assign to the generated plot.

    Returns
    -------
    fig : matplotlib.pyploy.Figure
        The Figure object which contains the Axes of the new plot.
    """
    # make subplot
    fig, ax = pyplot.subplots()

    # 2D plot of lines within y
    if type(y) is dict:
        for label, data in y.items():
            ax.plot(x, data, label=label)
    elif type(y) is list:
        ax.plot(x, y)

    ax.set_title(title)

    return fig


if __name__ == "__main__":
    args = get_args()

    # process log
    episode_dict = process_log(args.log_path, args.worker_episode_number)

    # make plots (lead, wing, region - xyz)
    fig = plot(episode_dict["step_number"], episode_dict["lead_x"], "lead x v. step number")
    fig.savefig(args.output + "lead_x.png")

    fig = plot(episode_dict["step_number"], episode_dict["lead_y"], "lead y v. step number")
    fig.savefig(args.output + "lead_y.png")

    fig = plot(episode_dict["step_number"], episode_dict["wingman_x"], "wingman x v. step number")
    fig.savefig(args.output + "wingman_x.png")

    fig = plot(episode_dict["step_number"], episode_dict["wingman_y"], "wingman y v. step number")
    fig.savefig(args.output + "wingman_y.png")

    fig = plot(episode_dict["step_number"], episode_dict["rejoin_region_x"], "rejoin region x v. step number")
    fig.savefig(args.output + "rejoin_region_x.png")

    fig = plot(episode_dict["step_number"], episode_dict["rejoin_region_y"], "rejoin region y v. step number")
    fig.savefig(args.output + "rejoin_region_y.png")

    if len(episode_dict["lead_z"]) == len(episode_dict["step_number"]):
        # generate z axis plots
        fig = plot(episode_dict["step_number"], episode_dict["lead_z"], "lead z v. step number")
        fig.savefig(args.output + "lead_z.png")

        fig = plot(episode_dict["step_number"], episode_dict["wingman_z"], "wingman z v. step number")
        fig.savefig(args.output + "wingman_z.png")

        fig = plot(episode_dict["step_number"], episode_dict["rejoin_region_z"], "rejoin region z v. step number")
        fig.savefig(args.output + "rejoin_region_z.png")
