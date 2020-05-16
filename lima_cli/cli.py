#
# Desired interface:
#
# $ lima basler --address=192.168.1.1 acquire -n 10 -e 0.1
# $ lima basler --address=192.168.1.1 info
#

__all__ = ['main']

import asyncio
import functools
import pkg_resources

import click

from .tool import table_style, max_width


def register_lima_camera_commands(group):
    """
    Return commands for those cameras who registered themselves
    with an entry point
    """
    for ep in pkg_resources.iter_entry_points('lima.cli.camera'):
        group.add_command(ep.load())

    group.scans = []
    for ep in pkg_resources.iter_entry_points('lima.cli.camera.scan'):
        group.scans.append((ep.name, ep.load()))


@click.group('lima')
@click.pass_context
def cli(ctx):
    """Lima CLI"""
    ctx.ensure_object(dict)


async def _scan(timeout):
    loop = asyncio.get_running_loop()

    async def detector_scan(scan, name, timeout):
        if asyncio.iscoroutinefunction(scan):
            task = asyncio.create_task(scan(timeout=timeout))
        else:
            scan = functools.partial(scan, timeout=timeout)
            task = loop.run_in_executor(None, scan)
        return name, (await task)

    tasks = []
    for name, scan in cli.scans:
        task = asyncio.create_task(detector_scan(scan, name, timeout=timeout))
        tasks.append(task)

    tables, errors = [], []
    for future in asyncio.as_completed(tasks, timeout=timeout+0.1):
        try:
            tables.append(await future)
        except Exception as error:
            errors.append((name, error))
    return tables, errors


@cli.command("scan")
@click.option('--timeout', default=2.0)
@table_style
@max_width
def scan(timeout, table_style, max_width):
    tables, errors = asyncio.run(_scan(timeout))
    for name, table in tables:
        if len(table):
            style = getattr(table, "STYLE_" + table_style.upper())
            table.set_style(style)
            table.max_table_width = max_width
            super_table = type(table)()
            super_table.column_headers = [name]
            super_table.append_row([table])
            super_table.set_style(style)
            super_table.max_table_width = max_width
            click.echo(name+":")
            click.echo(table)
            click.echo()
    for name, error in errors:
        click.echo('{} error: {!r}'.format(name, error), err=True)


def main():
    register_lima_camera_commands(cli)
    cli()


if __name__ == "__main__":
    main()
