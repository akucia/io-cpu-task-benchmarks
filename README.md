# Summary

The purpose of this project is to benchmark and optimized image download, cropping and upload task.
It's a problem with both IO and CPU bound tasks.

tdlr: 
- use whatever solution you want it's crucial to upload resulting images in parallel.
- Using mulitple ThreadPools in the code is probably cheaper to run then multiprocessing (less CPUs)
and it's easier to implement than full asyncio solution.
- Multiprocessing might be the best solution if the number of tasks is high enough to justify th extra 
time to setup and join multiple processes.

# Usage
Checkout [Taskfile.yml](Taskfile.yml) for available commands.
You'll need [Task](https://taskfile.dev) for that!
# Plots

## Images read and saved from Google Cloud Storage
![all-remote.png](all-remote.png)
### Asynchronous
- Uses asyncio and gcloud-aio-storage to download and upload files to Google Cloud Storage.
- To limit concurrency and prevent timout errors the concurrency is limited to at most 10 concurrent tasks
 and at most 10 concurrent image uploads.
  - Check out this great blog post on [how to limit concurrency](https://death.andgravity.com/limit-concurrency)
### Multiprocessing
- Uses parallel process to run the tasks.
- At most 6 processes are used to run task and an additional 7th process is used to process loging.
- Every process uses a thread pool to upload resulting image crops to Google Cloud Storage.
- Official Google Cloud Storage python client is used to download and upload files.
### Multithreading
- Uses parallel threads to run the tasks.
- At most 10 threads in the main process are used to run tasks and an additional separate process is used to process loging 
(to keep things similar to multiprocessing).
- Every thread uses a thread pool to upload resulting image crops to Google Cloud Storage.
- Official Google Cloud Storage python client is used to download and upload files.
## Images read and saved from local disk
![all-local.png](all-local.png)


# References
- inspired by "Shared CPU-I/O Workload" chapter in [High Performance Python](https://www.oreilly.com/library/view/high-performance-python/9781492055013/)
