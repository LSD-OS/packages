"""System configuration backend for LSD-Welcome.

Applies live environment settings immediately and persists them for the
installed system and subsequent boot stages.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time


def _sudo_write_file(file_path: str | Path, content: str) -> None:
    """Helper to write content to a root-owned file using sudo tee."""
    target_path = Path(file_path)
    parent_dir = target_path.parent
    subprocess.run(["sudo", "mkdir", "-p", str(parent_dir)], check=False)
    subprocess.run(
        ["sudo", "tee", str(target_path)],
        input=content.encode("utf-8"),
        stdout=subprocess.DEVNULL,
        check=True,
    )


def apply_language(locale_str: str) -> None:
    """Applies system language and persists locale configurations.
    
    Updates:
    - Current process environment (LANG)
    - /etc/locale.conf
    - /etc/profile.d/locale.sh
    - /etc/lsd-welcome/env (sourced by cosmic-greeter)
    """
    os.environ["LANG"] = locale_str

    # Persist in /etc/locale.conf
    _sudo_write_file("/etc/locale.conf", f"LANG={locale_str}\n")

    # Persist in profile.d for interactive shells
    _sudo_write_file("/etc/profile.d/locale.sh", f"export LANG={locale_str}\n")

    # Persist for cosmic-greeter environment
    _sudo_write_file("/etc/lsd-welcome/env", f"export LANG={locale_str}\n")

    # Fast cache for UI / legacy scripts
    lang_code = locale_str.split(".")[0].split("_")[0]
    try:
        Path("/tmp/.lsd_welcome_lang").write_text(f"{lang_code}\n", encoding="utf-8")
    except OSError:
        pass


def apply_keyboard(xkb_layout: str, xkb_variant: str, vconsole_keymap: str) -> None:
    """Applies keyboard layout for COSMIC desktop and virtual console.
    
    Updates:
    - /usr/share/cosmic/com.system76.CosmicComp/v1/xkb_config (RON format)
    - /etc/vconsole.conf (KEYMAP)
    - Runs loadkeys for current console session
    """
    ron_content = (
        f'(rules: "", model: "", layout: "{xkb_layout}", '
        f'variant: "{xkb_variant}", options: None)\n'
    )
    _sudo_write_file(
        "/usr/share/cosmic/com.system76.CosmicComp/v1/xkb_config",
        ron_content,
    )

    vconsole_content = f"KEYMAP={vconsole_keymap}\n"
    _sudo_write_file("/etc/vconsole.conf", vconsole_content)

    subprocess.run(["sudo", "loadkeys", vconsole_keymap], check=False)


def apply_timezone(timezone_str: str) -> None:
    """Applies system timezone and updates /etc/localtime symlink.
    
    Updates:
    - Current process TZ environment
    - /etc/localtime -> /usr/share/zoneinfo/<timezone_str>
    - /etc/timezone
    """
    os.environ["TZ"] = timezone_str
    if hasattr(time, "tzset"):
        try:
            time.tzset()
        except Exception:
            pass

    target_zoneinfo = f"/usr/share/zoneinfo/{timezone_str}"
    subprocess.run(
        ["sudo", "ln", "-sf", target_zoneinfo, "/etc/localtime"],
        check=True,
    )

    _sudo_write_file("/etc/timezone", f"{timezone_str}\n")


def apply_cosmic_theme(theme_mode: str) -> None:
    """Configures COSMIC theme mode (Dark or Light).
    
    Updates:
    - ~/.config/cosmic/com.system76.CosmicTheme.Mode/v1/mode
    - /etc/lsd-welcome/theme
    """
    mode_cap = "Dark" if theme_mode.lower() == "dark" else "Light"
    ron_content = f"(mode: {mode_cap})\n"

    # User level config
    try:
        user_dir = Path.home() / ".config" / "cosmic" / "com.system76.CosmicTheme.Mode" / "v1"
        user_dir.mkdir(parents=True, exist_ok=True)
        mode_file = user_dir / "mode"
        mode_file.write_text(ron_content)
    except OSError:
        pass

    # Persist in /etc/lsd-welcome for system-wide / greeter reference
    _sudo_write_file("/etc/lsd-welcome/theme", ron_content)


def set_install_mode(mode: str) -> None:
    """Persists installation mode ('online' or 'offline') in /etc/lsd-welcome/install_mode."""
    normalized_mode = mode.strip().lower()
    _sudo_write_file("/etc/lsd-welcome/install_mode", f"{normalized_mode}\n")


def get_install_mode() -> str:
    """Reads current installation mode from /etc/lsd-welcome/install_mode."""
    path = Path("/etc/lsd-welcome/install_mode")
    if path.exists():
        try:
            mode = path.read_text(encoding="utf-8").strip().lower()
            if mode in ("online", "offline"):
                return mode
        except OSError:
            pass
    return "online"
