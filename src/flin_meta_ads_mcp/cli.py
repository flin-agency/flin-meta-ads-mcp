from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass

from . import __version__
from .credentials import credentials_path, save_credentials
from .login import DEFAULT_REDIRECT_URI, LoginSettings, browser_login


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only Meta Ads MCP server and browser login")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    login = commands.add_parser("login", help="Sign in to Meta and save credentials locally")
    login.add_argument("--app-id", default=os.environ.get("META_APP_ID"))
    login.add_argument("--config-id", default=os.environ.get("META_LOGIN_CONFIG_ID"))
    login.add_argument("--redirect-uri", default=os.environ.get("META_REDIRECT_URI", DEFAULT_REDIRECT_URI))
    login.add_argument("--manual", action="store_true", help="Paste callback URL from a registered HTTPS redirect")
    login.add_argument("--no-browser", action="store_true", help="Print the login URL without opening it")
    login.add_argument("--timeout", type=float, default=180, help="Local callback timeout in seconds")
    args = parser.parse_args(argv)
    if args.command is None:
        from .server import main as serve
        serve()
        return
    try:
        app_id = args.app_id or input("Meta App ID: ")
        app_secret = os.environ.get("META_APP_SECRET") or getpass("Meta App Secret (App-Geheimcode): ")
        settings = LoginSettings(
            app_id=app_id.strip(), app_secret=app_secret.strip(),
            api_version=os.environ.get("META_GRAPH_API_VERSION", "v21.0"),
            redirect_uri=args.redirect_uri, config_id=args.config_id,
        )
        credentials = browser_login(
            settings, manual=args.manual, no_browser=args.no_browser, timeout=args.timeout,
        )
        path = credentials_path(os.environ)
        save_credentials(path, credentials)
        print(f"Login successful. Credentials saved to {path}. Restart your MCP client.")
        if os.environ.get("META_ACCESS_TOKEN"):
            print("Remove META_ACCESS_TOKEN from the MCP configuration to use this saved login.")
    except ValueError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except OSError:
        print("Login failed: could not store credentials. Check META_AUTH_FILE permissions.", file=sys.stderr)
        raise SystemExit(1) from None
    except (KeyboardInterrupt, EOFError):
        print("Login cancelled.", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
