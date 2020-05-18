import sys
import asyncio
import pathlib
import functools

import Lima
import click


# ModuleNotFoundError added in python 3.6
try:
    ModuleNotFoundError
except AttributeError:
    ModuleNotFoundError = ImportError


class CameraNotFoundError(click.ClickException):
    exit_code = 2


def get_lima_camera_names():
    """Find installed lima cameras"""
    cameras = []
    path = Lima.__path__
    for path in Lima.__path__:
        path = pathlib.Path(path)
        if path.is_dir():
            for item in path.iterdir():
                name = item.name
                if name != 'Core' and item.is_dir():
                    cameras.append(name)
    return cameras


def load(package_name):
    __import__(package_name)
    return sys.modules[package_name]


def camera_module(name):
    try:
        return load('Lima.' + name)
    except ModuleNotFoundError:
        raise CameraNotFoundError('{} is not installed'.format(name))


async def scan(scans, timeout):
    loop = asyncio.get_running_loop()

    async def detector_scan(scan, name, timeout):
        if asyncio.iscoroutinefunction(scan):
            task = asyncio.create_task(scan(timeout=timeout))
        else:
            scan = functools.partial(scan, timeout=timeout)
            task = loop.run_in_executor(None, scan)
        return name, (await task)

    tasks = []
    for name, scan in scans:
        task = asyncio.create_task(detector_scan(scan, name, timeout=timeout))
        tasks.append(task)

    tables, errors = [], []
    for future in asyncio.as_completed(tasks, timeout=timeout+0.1):
        try:
            tables.append(await future)
        except Exception as error:
            errors.append((name, error))
    return tables, errors



