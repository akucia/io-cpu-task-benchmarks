import logging
import logging.handlers
import os
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from multiprocessing import Queue, Process

import PIL
import click
import numpy as np
from tqdm import tqdm

from mixed_io_cpu_task.cropping import crop_with_pil
from mixed_io_cpu_task.io_utils import (
    download_crops_and_image,
    save_image_buffers,
    remove_dir,
)

from mixed_io_cpu_task.logging_utils import configure_logger


def logger_thread(q, log_filename: str):
    """logger thread consumes logging records from the queue and logs them."""
    logging.basicConfig()
    logger = logging.getLogger("default")
    configure_logger(logger, log_filename)
    while record := q.get():
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def logger_queue_handler_initializer(logging_queue: Queue):
    """worker initializer creates a new logger for every worker process and uses shared logging queue
    to log to the main process
    """
    queue_handler = logging.handlers.QueueHandler(logging_queue)
    root = logging.getLogger("default")
    root.addHandler(queue_handler)
    root.setLevel(logging.DEBUG)
    root.debug("worker initialized")


def run(i, crops, input_image, output_dir, max_save_threads):
    image_buffer, crops_to_cut = download_crops_and_image(
        crops, input_image, trace_id=str(i)
    )
    buffers = crop_with_pil(image_buffer, crops_to_cut, trace_id=str(i))
    save_image_buffers(
        buffers, output_dir, trace_id=str(i), max_threads=max_save_threads
    )


@click.command()
@click.argument("input_image", type=click.Path(path_type=str))
@click.argument("crops", type=click.Path(path_type=str))
@click.argument("output_dir", type=click.Path(path_type=str))
@click.option("--num-repeats", "-r", default=1, help="Number of repeats")
@click.option("--remove", "-rm", is_flag=True, help="Remove output dir before running")
@click.option(
    "--executor",
    "-e",
    default="thread",
    help="Executor to use",
    type=click.Choice(["thread", "process"]),
)
def multithreading(
    input_image: str,
    crops: str,
    output_dir: str,
    num_repeats: int,
    remove: bool,
    executor: str,
):
    # set a queue for the logging messages
    logging_queue = Queue()

    # setup the logger
    logging.basicConfig()
    logger = logging.getLogger("default")
    log_filename = f"multi-{executor}"
    if "gs://" in output_dir:
        log_filename += "-remote"
    else:
        log_filename += "-local"

    logger_queue_handler_initializer(logging_queue)
    # initialize a thread to consume the logging messages
    logging_process = Process(
        target=logger_thread,
        args=(logging_queue, log_filename),
    )
    logging_process.start()

    logger.debug(f"PIL: {PIL.__version__}")
    logger.debug(f"NumPy: {np.__version__}")
    logger.info(f"input image {input_image}, input crops {crops}")

    # cleanup old data
    if remove:
        logger.debug(f"Removing output dir {output_dir}")
        remove_dir(output_dir)
    if not output_dir.startswith("gs://"):
        pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)

    if executor == "process":
        Executor = ProcessPoolExecutor
        max_workers = os.cpu_count() // 2
    else:
        Executor = ThreadPoolExecutor
        max_workers = os.cpu_count() // 2 + 4

    logger.info(
        f"CPU count: {os.cpu_count()}, will use {max_workers} workers with {Executor.__name__}"
    )

    # start benchmark
    start = time.perf_counter()
    # initialize all processes in the executor with the same logging queue
    with Executor(
        max_workers,
        initializer=logger_queue_handler_initializer,
        initargs=(logging_queue,),
    ) as executor:
        futures = []
        for i in range(num_repeats):
            future = executor.submit(
                run, i, crops, input_image, output_dir, max_workers
            )
            futures.append(future)
        for future in tqdm(as_completed(futures), total=len(futures)):
            future.result()

    elapsed = time.perf_counter() - start
    logger.info(
        f"Elapsed {elapsed:.2f} seconds, average {num_repeats/elapsed:.2f} img/s"
    )
    logging_queue.put(None)
    logging_process.join()
