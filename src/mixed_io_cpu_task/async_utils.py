import asyncio


async def limit_concurrency(aws, limit):
    """Source: https://death.andgravity.com/limit-concurrency
    Great blog post - you should check it out!
    """
    aws = iter(aws)
    aws_ended = False
    pending = set()

    while pending or not aws_ended:
        while len(pending) < limit and not aws_ended:
            try:
                aw = next(aws)
            except StopIteration:
                aws_ended = True
            else:
                pending.add(asyncio.ensure_future(aw))

        if not pending:
            return

        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        while done:
            yield done.pop()
