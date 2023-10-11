import pathlib

import click
import matplotlib.pyplot as plt
import pandas as pd
import json
import distinctipy


@click.command()
@click.argument("input_log_file", type=click.Path(path_type=pathlib.Path))
@click.option("--plot-file-name", "-p", type=str, default=None)
def plot_logs(input_log_file: pathlib.Path, plot_file_name: str = None):
    if "*" in str(input_log_file):
        glob_pattern = str(input_log_file.name)
        input_log_file = pathlib.Path(input_log_file).parent
        log_files = sorted(input_log_file.glob(glob_pattern))
        # filter out empty log files
        log_files = [log_file for log_file in log_files if log_file.stat().st_size != 0]
        fig, axarr = plt.subplots(len(log_files), sharex=True, figsize=(10, 10))
        for log_file, ax in zip(log_files, axarr):
            # plot every file on a separate subplots vertically but keep them in the same figure sharing x-axis
            _plot_file(log_file, ax=ax)
        axarr[-1].set_xlabel("seconds")
        filename = plot_file_name or f"{input_log_file.parent.stem}.png"
        plt.savefig(filename)
    else:
        _plot_file(input_log_file)
        filename = plot_file_name or f"{input_log_file.stem}.png"
        plt.savefig(filename)


def _plot_file(input_log_file: pathlib.Path, ax=None):
    if ax is None:
        _, ax = plt.subplots()

    with input_log_file.open() as f:
        records = [json.loads(line) for line in f]
    if not records:
        return
    # df contains columns asctime levelname name message trace_id
    df = pd.DataFrame.from_records(records)
    df = df.drop_duplicates()
    # drop rows without trace_id
    if "trace_id" not in df.columns:
        return
    df = df.dropna(subset=["trace_id"])
    # convert timestamp to datetime
    # asctime example "2023-10-09 08:09:54,867"
    df["asctime"] = pd.to_datetime(df["asctime"].values, format="%Y-%m-%d %H:%M:%S,%f")
    df["asctime"] = df["asctime"].map(lambda x: x.timestamp())

    # nomalize time to start from 0
    df["asctime"] = df["asctime"] - df["asctime"].min()

    # assign different color to every message
    available_colors = distinctipy.get_colors(len(df["message"].unique()), rng=42)
    message_to_color = dict(zip(df["message"].unique(), available_colors))
    df["color"] = df["message"].map(message_to_color)
    # assign different y index to every trace id
    # df["y"] = df["trace_id"].astype("category").cat.codes
    df["y"] = df["trace_id"].map(lambda x: int(x))
    # group by trace id and plot
    for trace_id, group in df.groupby("trace_id"):
        for _, point in group.iterrows():
            ax.scatter(
                point["asctime"],
                point["y"],
                color=point["color"],
            )
        # draw dashed line from min to max asctime
        ax.plot(
            [group["asctime"].min(), group["asctime"].max()],
            [point["y"], point["y"]],
            linestyle=":",
            color="black",
            linewidth=0.5,
        )
    # set plot title to log file name
    ax.set_title(input_log_file.name)
    # add grids and subgrids
    ax.grid()
    ax.set_ylabel("trace id")
