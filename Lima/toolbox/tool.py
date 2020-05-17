import sys
import pathlib
import functools

import click
import Lima.Core


# ModuleNotFoundError added in python 3.6
try:
    ModuleNotFoundError
except AttributeError:
    ModuleNotFoundError = ImportError


class CameraNotFoundError(click.ClickException):
    exit_code = 2


@functools.lru_cache()
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


def camera(func=None, **attrs):
    """Helper click group command decorator"""
    if func is None:
        return functools.partial(camera, **attrs)

    @functools.wraps(func)
    def decorator(ctx, *args, **kwargs):
        ctx.obj['interface'] = func(*args, **kwargs)

    group = click.group(**attrs)(click.pass_context(decorator))

    from .info import info
    from .acquire import acquire

    group.add_command(info)
    group.add_command(acquire)

    return group


def load(package_name):
    __import__(package_name)
    return sys.modules[package_name]


def camera_module(name):
    try:
        return load('Lima.' + name)
    except ModuleNotFoundError:
        raise CameraNotFoundError('{} is not installed'.format(name))


url = click.option("-u", "--url", type=str)

table_style = click.option(
    "--style", "table_style", type=str, default="compact",
    show_default=True, help="table style"
)

max_width = click.option(
    "--max-width",
    type=int,
    default=lambda: click.get_terminal_size()[0],
    help="maximum width",
)
