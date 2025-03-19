# app/utils/threading_utils.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(executor, func, *args)
