#
# Desired interface:
#
# $ lima basler --address=192.168.1.1 acquire -n 10 -e 0.1
# $ lima basler --address=192.168.1.1 info
#

import click


@click.group(chain=True)
@click.pass_context
def cli(ctx):
    """Lima CLI"""
    click.echo("cli!")
    ctx.ensure_object(dict)


@click.command("info")
@click.pass_context
def info(ctx):
    click.echo("info " + ctx.obj["interface"])


@click.command("acquire")
@click.pass_context
def acquire(ctx):
    click.echo("acquire " + ctx.obj["interface"])


# -----------------------------------------------------------------------------
# in basler:


@click.command("basler")
@click.option("--address", type=str)
@click.pass_context
def basler(ctx, address):
    # build interface
    ctx.obj["interface"] = f"Basler@{address}"

# -----------------------------------------------------------------------------


def main():
    # TODO: find command plugins
    cli.add_command(basler)

    cli.add_command(info)
    cli.add_command(acquire)

    cli()


if __name__ == "__main__":
    main()
