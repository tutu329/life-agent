from typing import Callable, Dict, List, Type
import functools
from pydantic import BaseModel, Field, ConfigDict
from concurrent.futures import ThreadPoolExecutor, Future
from fastapi import FastAPI
import asyncio, queue
from sse_starlette.sse import EventSourceResponse   # pip install sse-starlette


