import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

import chromedriver_autoinstaller
import httpx
from rich import print
from rich.pretty import pprint
from tda import auth
from tda.client import Client


@dataclass(init=True)
class TDA:
    api_key: str
    callback_uri: str

    def get_client(self) -> Client:
        """Get or create a new TDA client."""

        token_path = "token.json"  # nosec - Tokens must be store in a flat file.
        api_string = f"{self.api_key}@AMER.OAUTHAP"

        try:
            client = auth.client_from_token_file(
                token_path, api_string, enforce_enums=False
            )
        except FileNotFoundError:
            from selenium import webdriver

            chromedriver_autoinstaller.install(True)
            with webdriver.Chrome() as driver:
                try:
                    client = auth.client_from_login_flow(
                        driver,
                        api_string,
                        self.callback_uri,
                        token_path,
                        enforce_enums=False,
                    )
                except Exception as e:
                    print("[bold red]Unable to authorize client. Aborting application!")
                    print(f"[bold red]{e}[/bold red]")
                    sys.exit()

        if isinstance(client, Client):
            return client

        print("[bold red]Invalid client. EXITING!")
        sys.exit()

    def get_account(self, account) -> Any:
        account = self.get_client().get_account(account, fields=["orders", "positions"])

        if account.status_code != httpx.codes.OK:
            print(
                f"[bold red]Get Account Error. Response Code {account.status_code}.[/bold red]"
            )
            pprint(account.content)
            sys.exit()

        return account.json()

    def get_orders(self, account) -> Any:
        dt = datetime.now()
        start = datetime.combine(dt, datetime.min.time()) + timedelta(-4)
        end = datetime.combine(dt, datetime.max.time())

        orders = self.get_client().get_orders_by_path(
            account,
            from_entered_datetime=start,
            to_entered_datetime=end,
            status="FILLED",
        )

        if orders.status_code != httpx.codes.OK:
            print(
                f"[bold red]Get Account Error. Response Code {orders.status_code}.[/bold red]"
            )
            pprint(orders.content)
            sys.exit()

        return orders.json()

    def get_hours_for_single_market(self, date: datetime) -> Dict[Any, Any]:
        hours = self.get_client().get_hours_for_single_market(
            Client.Markets.OPTION, date
        )

        if hours.status_code != httpx.codes.OK:
            hours.raise_for_status()

        return dict(hours.json())
