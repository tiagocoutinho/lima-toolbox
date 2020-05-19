import asyncio
import urllib.parse

import click

from Lima.toolbox.cli import camera, url, table_style, max_width
from Lima.toolbox.util import camera_module
from Lima.toolbox.network import get_subnet_addresses, get_host_by_addr

DEFAULT_HTTP_PORT = 8000


@camera(name="eiger")
@url
def eiger(url):
    """eiger detector specific commands"""
    if url is None:
        return
    Eiger = camera_module('Eiger')
    if not url.startswith("http://"):
        url = "http://" + url
    url = urllib.parse.urlparse(url)
    port = DEFAULT_HTTP_PORT if url.port is None else url.port
    eiger = Eiger.Camera(url.hostname, port)
    interface = Eiger.Interface(eiger)
    return interface


async def find_detectors(port=DEFAULT_HTTP_PORT, timeout=2.0):
    import aiohttp

    async def get(addr):
        async with aiohttp.ClientSession() as session:
            try:
                r = await session.get(
                    f"http://{addr}:{port}/detector/api/version/")
                if r.status != 200:
                    return
                version = (await r.json())['value']
            except Exception:
                return
            host = await get_host_by_addr(addr)
            return host, port, version

    detectors = []
    addresses = get_subnet_addresses()
    coros = [get(host) for host in addresses]
    try:
        for task in asyncio.as_completed(coros, timeout=timeout):
            detector = await task
            if detector is not None:
                detectors.append(detector)
    except asyncio.TimeoutError:
        pass
    return detectors


def detector_table(detectors):
    import beautifultable

    width = click.get_terminal_size()[0]
    table = beautifultable.BeautifulTable(max_width=width)
    table.column_headers = 'Host', 'Alias(es)', 'Address(es)', 'Port', 'API'
    for detector in detectors:
        host, port, version = detector
        aliases = '\n'.join(host.aliases)
        addresses = '\n'.join(host.addresses)
        table.append_row((host.name, aliases, addresses, port, version))
    return table


async def scan(port=DEFAULT_HTTP_PORT, timeout=2):
    detectors = await find_detectors(port, timeout)
    return detector_table(detectors)


@eiger.command("scan")
@click.option('-p', '--port', default=DEFAULT_HTTP_PORT)
@click.option('--timeout', default=2.0)
@table_style
@max_width
def eiger_scan(port, timeout, table_style, max_width):
    """show accessible eiger detectors on the network"""
    table = asyncio.run(scan(port, timeout))
    style = getattr(table, "STYLE_" + table_style.upper())
    table.set_style(style)
    table.max_table_width = max_width
    click.echo(table)
