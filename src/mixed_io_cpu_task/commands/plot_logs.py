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
        fig, axarr = plt.subplots(len(log_files), sharex=True, figsize=(15, 20))
        for log_file, ax in zip(log_files, axarr):
            # plot every file on a separate subplots vertically but keep them in the same figure sharing x-axis
            # plot labels only on the last subplot
            _plot_file(log_file, ax=ax, labels=log_file == log_files[0])
        # set x-axis label
        axarr[-1].set_xlabel("seconds")
        # add legend on the right
        fig.subplots_adjust(right=0.8)
        axarr[0].legend(
            loc="upper left",
            bbox_to_anchor=(1.02, -0.5),
            fancybox=False,
            shadow=False,
        )
        filename = plot_file_name or f"{input_log_file.parent.stem}.png"
        plt.savefig(filename)
    else:
        _plot_file(input_log_file)
        filename = plot_file_name or f"{input_log_file.stem}.png"
        plt.savefig(filename)


def _plot_file(input_log_file: pathlib.Path, ax=None, labels=False):
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
    single_trace_id = list(set(df["trace_id"]))[0]

    # cut message to 100 characters
    df["message"] = df["message"].map(lambda x: x[:100])
    # assign different color to every message
    available_colors = distinctipy.get_colors(len(df["message"].unique()), rng=42)
    message_to_color = dict(zip(df["message"].unique(), available_colors))
    df["color"] = df["message"].map(message_to_color)
    # assign different y index to every trace id
    df["y"] = df["trace_id"].astype("category").cat.codes
    df = df.sort_values(by=["y", "asctime"])
    # group by trace id and plot
    for trace_id, group in df.groupby("trace_id"):
        # sort by asctime
        for _, point in group.iterrows():
            message = point["message"]
            # break message into lines if longer than 50 characters
            if len(message) > 30:
                message = "\n".join(
                    [message[i : i + 50] for i in range(0, len(message), 50)]
                )
            ax.scatter(
                point["asctime"],
                point["y"],
                color=point["color"],
                label=message if labels and trace_id == single_trace_id else None,
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
