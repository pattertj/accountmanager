import sys

import keyring
import typer
from rich import print


def configure_keychain(key: str) -> str:
    existing_key = keyring.get_password("system", key)
    new_key = typer.prompt(key, existing_key)
    try:
        keyring.set_password("system", key, new_key)
        return str(new_key)
    except keyring.errors.PasswordSetError:
        print(f"[bold red]Failed to store {key}[/bold red]")
        sys.exit()


def read_keychain(key: str) -> str:
    key_value = keyring.get_password("system", key)

    # If no API key in the keychain, prompt for it and set it.
    if key_value is None:
        print(f"[bold red]{key} not set.[/bold red]")
        return configure_keychain(key)
    return str(key_value)
