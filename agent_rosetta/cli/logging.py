import click

TAB_WIDTH = 4
TAB = " " * TAB_WIDTH


def log_success(message: str):
    click.echo(click.style(f"{TAB}✓", fg="green", bold=True) + f" {message}")


def log_warning(message: str):
    click.echo(click.style(f"{TAB}!", fg="yellow", bold=True) + f" {message}")


def log_error(message: str):
    click.echo(click.style(f"{TAB}✗", fg="red", bold=True) + f" {message}")


def log_info(message: str = None):
    if message is None:
        click.echo()
    else:
        click.echo(click.style(message, dim=True))
