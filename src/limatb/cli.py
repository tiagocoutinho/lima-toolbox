#
# Desired interface:
#
# $ lima basler --address=192.168.1.1 acquire -n 10 -e 0.1
# $ lima basler --address=192.168.1.1 info
#

__all__ = ['main']

import asyncio
import logging
import functools

import click

from .util import scan


log = logging.getLogger("limatb")


url = click.option("-u", "--url", type=str)


table_style = click.option(
    "--table-style", "table_style", type=str, default="compact",
    show_default=True, help="table style"
)


max_width = click.option(
    "--max-width",
    type=int,
    default=lambda: click.get_terminal_size()[0],
    help="maximum width",
)


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


@click.group('limatb')
@click.pass_context
def cli(ctx):
    """
    Lima toolbox CLI

    Detector discovery, detector information, perform acquisitions and custom
    detector commands
    """
    ctx.ensure_object(dict)


@cli.command("scan")
@click.option('--timeout', default=2.0)
@table_style
@max_width
def lima_scan(timeout, table_style, max_width):
    """scan network for detectors"""
    tables, errors = asyncio.run(scan(cli.scans, timeout))
    for name, table in tables:
        if len(table.rows):
            style = getattr(table, "STYLE_" + table_style.upper())
            table.set_style(style)
            table.maxwidth = max_width
            click.echo(name+":")
            click.echo(table)
            click.echo()
    for error in errors:
        click.echo('error: {!r}'.format(error), err=True)


def register_lima_camera_commands(group):
    """
    Return commands for those cameras who registered themselves
    with an entry point
    """
    import pkg_resources
    for ep in pkg_resources.iter_entry_points('limatb.cli.camera'):
        try:
            group.add_command(ep.load())
        except Exception as error:
            log.debug('failed to register camera %s: %r', ep.name, error)

    group.scans = []
    for ep in pkg_resources.iter_entry_points('limatb.cli.camera.scan'):
        try:
            group.scans.append((ep.name, ep.load()))
        except Exception as error:
            log.debug('failed to register scan %s: %r', ep.name, error)


def main():
    register_lima_camera_commands(cli)
    cli()


if __name__ == "__main__":
    main()
