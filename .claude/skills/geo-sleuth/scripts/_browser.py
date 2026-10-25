"""Shared Chrome / Playwright Chromium launch and actionable setup errors."""
from __future__ import annotations

import os
import shutil

from _net import resolve_proxy

# Browser binaries tried after the Chrome channel and Playwright's own Chromium fail,
# e.g. a Chromium preinstalled for a different Playwright revision.
EXECUTABLE_CANDIDATES = ("/opt/pw-browsers/chromium", "chromium", "chromium-browser",
                         "google-chrome", "google-chrome-stable")


def _executables() -> list[str]:
    found = []
    env = os.environ.get("GEO_SLEUTH_BROWSER")
    for name in ([env] if env else []) + list(EXECUTABLE_CANDIDATES):
        path = name if os.path.isabs(name) else shutil.which(name)
        if path and os.access(path, os.X_OK) and path not in found:
            found.append(path)
    return found


async def launch_browser(playwright, proxy: str | None = None):
    value = resolve_proxy(proxy)
    options = {"headless": True, "timeout": 15000,
               "args": ["--disable-blink-features=AutomationControlled"]}
    if value:
        options["proxy"] = {"server": value.replace("socks5h://", "socks5://")}
    else:
        options["args"].append("--no-proxy-server")
    errors = []
    for channel in ("chrome", None):
        try:
            browser = await playwright.chromium.launch(
                **({"channel": channel} if channel else {}), **options)
            return browser, "Google Chrome" if channel else "Playwright Chromium"
        except Exception as exc:
            errors.append(f"{channel or 'chromium'}: {str(exc).splitlines()[0]}")
    for path in _executables():
        try:
            browser = await playwright.chromium.launch(executable_path=path, **options)
            return browser, f"Chromium ({path})"
        except Exception as exc:
            errors.append(f"{path}: {str(exc).splitlines()[0]}")
    raise RuntimeError(
        "Neither Google Chrome nor Playwright Chromium could start. "
        "Run `uvx playwright install chromium` and retry, or set GEO_SLEUTH_BROWSER "
        "to a Chrome/Chromium executable; on Linux, missing system libraries "
        "may require `uvx playwright install --with-deps chromium`. "
        + " | ".join(errors))
