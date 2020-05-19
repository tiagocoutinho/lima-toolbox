import click
import Lima.Core


def info_list(info):
    result = []
    for name in dir(info):
        if not name.startswith('get'):
            continue
        member = getattr(info, name)
        if callable(member):
            try:
                result.append((name[3:], member()))
            except Exception:
                pass
    return result


def info_text(info):
    dinfo = info if isinstance(info, (list, tuple)) else info_list(info)
    size = max(len(i[0]) for i in dinfo)
    template = "{{:>{}}}: {{}}".format(size)
    lines = (template.format(key, value) for key, value in dinfo)
    return '\n'.join(lines)


@click.command("info")
@click.pass_context
def info(ctx):
    """Shows information about the camera"""
    interface = ctx.obj['interface']
    info = interface.getHwCtrlObj(Lima.Core.HwCap.DetInfo)
    click.echo(info_text(info))
