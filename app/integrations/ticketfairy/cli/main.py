"""TicketFairy CLI entry point."""

import clicycle

from app.integrations.ticketfairy.cli.commands import cli


def main() -> None:
    """Main CLI entry point."""
    clicycle.configure(app_name="ticketfairy-submit")
    cli()


if __name__ == "__main__":
    main()
