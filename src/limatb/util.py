import sys
import asyncio
import pathlib
import functools

import pint
import click
import Lima.Core
from Lima.Core import CtControl, CtSaving


ur = pint.UnitRegistry()


ErrorMap = {
    CtControl.NoError:           "No error",
    CtControl.SaveUnknownError:  "Saving error",
    CtControl.SaveOpenError:     "Save file open error",
    CtControl.SaveCloseError:    "Save file close error",
    CtControl.SaveAccessError:   "Save access error",
    CtControl.SaveOverwriteError: "Save overwrite error",
    CtControl.SaveDiskFull:      "Save disk full",
    CtControl.SaveOverun:        "Save overrun",
    CtControl.ProcessingOverun:  "Soft Processing overrun",
    CtControl.CameraError:       "Camera Error",
}


FileFormat = {
    "hardware": CtSaving.HARDWARE_SPECIFIC,
    "raw": CtSaving.RAW,
    "edf": CtSaving.EDF,
    "edf-gz": CtSaving.EDFGZ,
    "edf-lz4": CtSaving.EDFLZ4,
    "edf-concat": CtSaving.EDFConcat,
    "cbf": CtSaving.CBFFormat,
    "cbf-mh": CtSaving.CBFMiniHeader,
    "nxs": CtSaving.NXS,
    "fits": CtSaving.FITS,
    "tiff": CtSaving.TIFFFormat,
    "hdf5": CtSaving.HDF5,
    "hdf5-gz": CtSaving.HDF5GZ,
    "hdf5-bs": CtSaving.HDF5BS,
}


SavingPolicy = {
    "abort": CtSaving.Abort,
    "overwrite": CtSaving.Overwrite,
    "append": CtSaving.Append
}
if hasattr(CtSaving, "MultiSet"):
    SavingPolicy["multiset"] = CtSaving.MultiSet


SavingMode = {
    "manual": CtSaving.Manual,
    "auto-frame": CtSaving.AutoFrame,
    "auto-header": CtSaving.AutoHeader
}


SavingManagedMode = {
    "software": CtSaving.Software,
    "hardware": CtSaving.Hardware
}
if hasattr(CtSaving, "Camera"):
    SavingPolicy["camera"] = CtSaving.Camera


TriggerMode = {
    "int": Lima.Core.IntTrig,
    "int-mult": Lima.Core.IntTrigMult,
    "ext-single": Lima.Core.ExtTrigSingle,
    "ext-mult": Lima.Core.ExtTrigMult,
    "ext-gate": Lima.Core.ExtGate,
    "ext-start-stop": Lima.Core.ExtStartStop,
    "ext-readout": Lima.Core.ExtTrigReadout
}

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
            errors.append(error)
    return tables, errors
