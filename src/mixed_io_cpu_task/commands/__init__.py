import click

from mixed_io_cpu_task.commands.serial import serial
from mixed_io_cpu_task.commands.asynchronous import asynchronous
from mixed_io_cpu_task.commands.plot_logs import plot_logs
from mixed_io_cpu_task.commands.concurrency import multi


@click.group()
def cli():
    pass


cli.add_command(serial)
cli.add_command(asynchronous)
cli.add_command(multi)
cli.add_command(plot_logs)
