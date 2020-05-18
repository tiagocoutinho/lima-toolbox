import click

from Lima.toolbox.cli import camera, url, table_style, max_width
from Lima.toolbox.util import camera_module

@camera(name="basler")
@url
@click.option("--packet-size", default=1500)
@click.option("--inter-packet-delay", default=0)
@click.option("--frame-transmission-delay", default=0)
def basler(
    url, packet_size,
    inter_packet_delay,
    frame_transmission_delay
):
    """basler detector specific commands"""
    if url is None:
        return
    Basler = camera_module('Basler')
    camera = Basler.Camera(url, packet_size)
    camera.setInterPacketDelay(inter_packet_delay)
    camera.setFrameTransmissionDelay(frame_transmission_delay)
    interface = Basler.Interface(camera)
    return interface


def scan(timeout=None):
    from pylonctl.camera import camera_table
    return camera_table()


@basler.command("scan")
@table_style
@max_width
def basler_scan(table_style, max_width):
    """show accessible basler detectors on the network"""
    table = scan()
    style = getattr(table, "STYLE_" + table_style.upper())
    table.set_style(style)
    table.max_table_width = max_width
    click.echo(table)
