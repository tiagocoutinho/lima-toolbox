import click
import Lima.Core


@click.command("info")
@click.pass_context
def info(ctx):
    """Shows information about the camera"""
    interface = ctx.obj['interface']
    info = interface.getHwCtrlObj(Lima.Core.HwCap.DetInfo)
    click.echo(f"Model: {info.getDetectorModel()}")
    click.echo(f"Type: {info.getDetectorType()}")
