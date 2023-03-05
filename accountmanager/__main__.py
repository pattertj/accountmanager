import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Tuple, Union

import pygsheets
import typer
from pygsheets import DataRange, Worksheet
from pygsheets.client import Client
from pytz import timezone
from rich import print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from accountmanager.broker import TDA
from accountmanager.keychain import read_keychain

console = Console()
app = typer.Typer(help="An awesome automated options entry tool.")
gc: Client = None


@app.command()
def run(
    account_number: str = typer.Option(
        "1234567890", help="Account Number to log data from.", prompt=True
    ),
    spreadsheet: str = typer.Option(
        "Trade Log", help="The Google Sheet to log to.", prompt=True
    ),
    balances_worksheet: str = typer.Option(
        "Balances",
        help="The Worksheet/Tab name within, to log Balances to.",
        prompt=True,
    ),
    trades_worksheet: str = typer.Option(
        "Trades", help="The Worksheet/Tab name within, to log Trades to.", prompt=True
    ),
    sheets_api_token: Path = typer.Option(
        "client_secret.json", help="Google Sheet API Token", prompt=True
    ),
) -> None:
    print("Validating [bold #00B624]TD Ameritrade[/bold #00B624] Configuration...")

    # Pull keychain values
    api_key, callback_uri = get_keychain_values()

    # Build TDA Client
    try:
        broker = TDA(api_key, callback_uri)
        broker.get_account(account_number)
    except Exception as e:
        print(e.__doc__)
        return

    print(
        ":thumbs_up: [bold #00B624]TD Ameritrade[/bold #00B624] Configuration is [bold #00B624]valid.[/bold #00B624]"
    )

    print("Validating [bold #0DC54C]Google Sheets[/bold #0DC54C] Configuration...")

    try:
        gc = pygsheets.authorize()
        sh = gc.open(spreadsheet)
        sh.worksheet_by_title(balances_worksheet)
        sh.worksheet_by_title(trades_worksheet)
    except Exception as e:
        print(e.__doc__)
        return

    print(
        ":thumbs_up: [bold #0DC54C]Google Sheets[/bold #0DC54C] is [bold #00B624]valid.[/bold #00B624]"
    )

    while True:
        open_dt, close_dt = get_next_market_hours(broker, datetime.now())

        getorders = True  # = process_market_hours(open_dt, close_dt)

        nlv, bp = get_account_details(account_number, broker)

        print_account_details(nlv, bp)

        save_to_sheets(nlv, bp, spreadsheet, balances_worksheet)

        if getorders:
            orders = get_orders(account_number, broker)
            save_orders(orders, spreadsheet, trades_worksheet)

        sleep(5)


def save_orders(orders, spreadsheet, worksheet):
    wks: Worksheet = gc.open(spreadsheet).worksheet_by_title(worksheet)

    header: DataRange = wks.range("A1:G1", returnas="range")  # get the range
    header.update_values(
        [
            [
                "Order ID",
                "Entered Time",
                "Fill Time",
                "Quantity",
                "Symbol",
                "Strikes",
                "Price",
            ]
        ]
    )

    values = wks.get_col(1, include_tailing_empty=False)
    next_blank_row = len(values) + 1

    order_rows = []

    for order in orders:
        if order["orderLegCollection"][0]["positionEffect"] == "OPENING":
            # Parse Symbol
            regex = re.search(
                r"_(\d+)[PC]([\d]+)$",
                order["orderLegCollection"][0]["instrument"]["symbol"],
            )

            # Strikes from regex
            strikes = regex.groups()[1]
            for leg in order["orderLegCollection"][1:]:
                leg_regex = re.search(
                    r"_(\d+)[PC]([\d]+)$", leg["instrument"]["symbol"]
                )
                strikes = f"{strikes}/{leg_regex.groups()[1]}"

            open_dt = datetime.strptime(
                order["enteredTime"], "%Y-%m-%dT%H:%M:%S%z"
            ).strftime("%-m/%-d/%Y, %-H:%M:%S")
            close_dt = datetime.strptime(
                order["closeTime"], "%Y-%m-%dT%H:%M:%S%z"
            ).strftime("%-m/%-d/%Y, %-H:%M:%S")

            order_deets = [
                str(order["orderId"]),
                open_dt,
                close_dt,
                order["filledQuantity"],
                order["orderLegCollection"][0]["instrument"]["underlyingSymbol"],
                strikes,
                order["price"],
            ]
            order_rows.append(order_deets)

    last_row = next_blank_row + max(0, len(order_rows) - 1)

    order_row: DataRange = wks.range(
        f"A{next_blank_row}:G{last_row}", returnas="range"
    )  # get the range
    order_row.update_values(order_rows)

    wks.apply_format(
        f"B{next_blank_row}:C{last_row}", {"numberFormat": {"type": "DATE_TIME"}}
    )
    wks.apply_format(
        f"G{next_blank_row}:G{last_row}", {"numberFormat": {"type": "CURRENCY"}}
    )


def print_account_details(nlv, bp):
    table = Table("Date", "NLV", "Buying Power", "P/L %", "BP Utilization")
    table.add_row(
        datetime.now().strftime("%m/%d/%Y"),
        f"${nlv:0,.0f}",
        f"${bp:0,.0f}",
        "0",
        f"{(100*(nlv-bp)/nlv):.1f}%",
    )
    console.print(table)


def get_account_details(account, broker: TDA):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Getting Account Details...", total=None)
        account_details = broker.get_account(account)

    nlv = account_details["securitiesAccount"]["currentBalances"]["liquidationValue"]
    bp = account_details["securitiesAccount"]["currentBalances"]["buyingPower"]
    return nlv, bp


def get_orders(account, broker: TDA):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Getting Orders...", total=None)
        orders = broker.get_orders(account)

    return orders


def save_to_sheets(nlv, bp, spreadsheet, worksheet):
    wks: Worksheet = gc.open(spreadsheet).worksheet_by_title(worksheet)
    values = wks.get_col(1, include_tailing_empty=False)
    next_blank_row = len(values) + 1

    nlv_row: DataRange = wks.range(
        f"A{next_blank_row}:C{next_blank_row}", returnas="range"
    )  # get the range
    nlv_row.update_values(
        [[datetime.now(timezone("EST")).strftime("%-m/%-d/%Y, %-H:%M:%S"), nlv, bp]]
    )

    wks.apply_format(f"A{next_blank_row}", {"numberFormat": {"type": "DATE_TIME"}})
    wks.apply_format(
        f"B{next_blank_row}:C{next_blank_row}", {"numberFormat": {"type": "CURRENCY"}}
    )


def process_market_hours(open_dt: datetime, close_dt: datetime):
    now = datetime.now(timezone("EST"))

    if now < open_dt:
        # Sleep until market open
        sleep_until(open_dt, now)
        return False
    elif open_dt < now < close_dt:
        # Sleep until close
        sleep_until(close_dt, now)
        return True
    elif now > close_dt:
        print("[bold red]Market Hours error.")
        sys.exit()


def sleep_until(date_to_sleep_to: datetime, now: datetime):
    time_to_sleep = (date_to_sleep_to - now).total_seconds()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(
            description=f"Sleeping until {date_to_sleep_to}...", total=None
        )
        sleep(time_to_sleep)


def get_keychain_values() -> Tuple[str, str]:
    api_key = read_keychain("tda_api_key")
    callback_uri = read_keychain("tda_callback_uri")
    return api_key, callback_uri


def get_market_hours(
    broker: TDA, date: datetime
) -> Tuple[Union[None, datetime], Union[None, datetime]]:
    hours = broker.get_hours_for_single_market(date)

    index = dict(hours["option"]).get("IND")
    if index is None:
        return None, None

    open_str = index["sessionHours"]["regularMarket"][0]["start"]
    close_str = index["sessionHours"]["regularMarket"][0]["end"]

    open_dt = datetime.strptime(open_str, "%Y-%m-%dT%H:%M:%S%z")
    close_dt = datetime.strptime(close_str, "%Y-%m-%dT%H:%M:%S%z")

    return open_dt, close_dt


def get_next_market_hours(broker: TDA, date: datetime) -> Tuple[datetime, datetime]:
    open, close = get_market_hours(broker, date)

    if open is None or close is None or close < datetime.now(timezone("EST")):
        return get_next_market_hours(broker, date + timedelta(days=1))

    return open, close


if __name__ == "__main__":
    app()
