"""Main Application and 6-step Wizard controller for LSD-Welcome.

Provides:
- WelcomeWizard: 6-step setup flow controller with headless support
- LsdWelcomeApplication: GTK4 / Libadwaita application entry point
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable

# Multi-path import resolution
try:
    from packages.lsd_welcome_pkg import system_config, network_manager, timezone_picker
    from packages.lsd_welcome_pkg.views import (
        WelcomeView,
        ThemeView,
        KeyboardView,
        NetworkView,
        TimezoneView,
        DecisionView,
    )
except ImportError:
    try:
        from . import system_config, network_manager, timezone_picker  # type: ignore
        from .views import (  # type: ignore
            WelcomeView,
            ThemeView,
            KeyboardView,
            NetworkView,
            TimezoneView,
            DecisionView,
        )
    except Exception:
        import system_config  # type: ignore
        import network_manager  # type: ignore
        import timezone_picker  # type: ignore
        from views import (  # type: ignore
            WelcomeView,
            ThemeView,
            KeyboardView,
            NetworkView,
            TimezoneView,
            DecisionView,
        )

# GTK4 & Libadwaita bindings
HAS_GTK = False
HAS_ADW = False

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, Gdk, Gio, GLib
    HAS_GTK = True
    try:
        gi.require_version("Adw", "1")
        from gi.repository import Adw
        HAS_ADW = True
    except (ImportError, ValueError):
        HAS_ADW = False
        Adw = None  # type: ignore
except (ImportError, ValueError):
    HAS_GTK = False
    Gtk = object  # type: ignore
    Adw = None  # type: ignore


COSMIC_CSS = """
/* COSMIC-harmonized dark aesthetic */
window.welcome-window {
    background-color: #1a1a24;
    color: #e6e6f0;
}

.welcome-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    margin-top: 6px;
}

.card {
    background-color: #242433;
    border-radius: 12px;
    border: 1px solid #333348;
    padding: 16px;
    transition: all 200ms ease;
}

.card:hover {
    border-color: #6366f1;
    background-color: #2a2a3c;
}

.theme-card-active {
    border: 2px solid #6366f1 !important;
    background-color: #2e2e42 !important;
}

.dim-label {
    color: #9ca3af;
    font-size: 13px;
}

.step-indicator {
    color: #818cf8;
    font-weight: 600;
    font-size: 13px;
}
"""


class WelcomeWizard:
    """Controller for the 6-step onboarding wizard."""

    TOTAL_STEPS = 6

    def __init__(self, headless: bool = False, app: Any = None) -> None:
        self.app = app
        is_headless = headless or (
            not HAS_GTK
            or not hasattr(Gdk, "Display")
            or Gdk.Display.get_default() is None
        )
        self.headless = is_headless
        self._current_step = 1

        # Instantiate the 6 views
        self.welcome_view = WelcomeView(headless=self.headless)
        self.theme_view = ThemeView(headless=self.headless)
        self.keyboard_view = KeyboardView(headless=self.headless)
        self.network_view = NetworkView(headless=self.headless)
        self.timezone_view = TimezoneView(headless=self.headless)
        self.decision_view = DecisionView(headless=self.headless)

        self.views = [
            self.welcome_view,
            self.theme_view,
            self.keyboard_view,
            self.network_view,
            self.timezone_view,
            self.decision_view,
        ]

        # Connect quit callback from decision view
        self.decision_view.connect_quit(self.close)

        self.window: Any = None
        if not self.headless:
            self._init_window()

    def get_total_steps(self) -> int:
        return self.TOTAL_STEPS

    def get_current_step(self) -> int:
        return self._current_step

    def next_step(self) -> None:
        """Advance to next step, applying changes of the current view."""
        if 1 <= self._current_step <= self.TOTAL_STEPS:
            current_view = self.views[self._current_step - 1]
            if hasattr(current_view, "apply_changes"):
                try:
                    current_view.apply_changes()
                except Exception:
                    pass

        if self._current_step < self.TOTAL_STEPS:
            self._current_step += 1
            self._update_navigation_ui()

    def previous_step(self) -> None:
        """Go back to previous step."""
        if self._current_step > 1:
            self._current_step -= 1
            self._update_navigation_ui()

    def go_to_step(self, step_number: int) -> None:
        """Navigate directly to specified step (1-6)."""
        target = max(1, min(self.TOTAL_STEPS, step_number))
        if target != self._current_step:
            self._current_step = target
            self._update_navigation_ui()

    def close(self) -> None:
        """Closes the wizard window and terminates the application."""
        if not self.headless and self.window:
            try:
                self.window.close()
            except Exception:
                pass
        if self.app and hasattr(self.app, "quit"):
            try:
                self.app.quit()
            except Exception:
                pass

    def present(self) -> None:
        """Presents the window if not headless."""
        if not self.headless and self.window:
            self.window.present()

    def _init_window(self) -> None:
        """Builds GTK4 / Libadwaita window interface."""
        self._load_css()

        if HAS_ADW:
            self.window = Adw.ApplicationWindow(application=self.app)
        else:
            self.window = Gtk.ApplicationWindow(application=self.app)

        self.window.set_title("Assistente de Boas-Vindas LSD_OS")
        self.window.set_default_size(920, 680)
        self.window.add_css_class("welcome-window")

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # HeaderBar
        if HAS_ADW:
            header = Adw.HeaderBar()
        else:
            header = Gtk.HeaderBar()
            header.set_show_title_buttons(True)
        main_box.append(header)

        # Content Stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)

        for i, view in enumerate(self.views):
            self.stack.add_named(view, f"step_{i+1}")

        main_box.append(self.stack)

        # Bottom Navigation Bar
        nav_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
            valign=Gtk.Align.END,
        )
        nav_box.set_margin_top(12)
        nav_box.set_margin_bottom(20)
        nav_box.set_margin_start(24)
        nav_box.set_margin_end(24)

        # Back Button
        self.back_button = Gtk.Button.new_with_label("Voltar")
        self.back_button.set_size_request(110, 42)
        self.back_button.connect("clicked", lambda _b: self.previous_step())
        nav_box.append(self.back_button)

        # Step indicator in center
        self.step_label = Gtk.Label(text="Passo 1 de 6")
        self.step_label.add_css_class("step-indicator")
        self.step_label.set_hexpand(True)
        self.step_label.set_halign(Gtk.Align.CENTER)
        nav_box.append(self.step_label)

        # Next Button
        self.next_button = Gtk.Button.new_with_label("Avançar")
        self.next_button.add_css_class("suggested-action")
        self.next_button.set_size_request(110, 42)
        self.next_button.connect("clicked", lambda _b: self.next_step())
        nav_box.append(self.next_button)

        main_box.append(nav_box)
        self.window.set_content(main_box) if HAS_ADW else self.window.set_child(main_box)

        self._update_navigation_ui()

    def _update_navigation_ui(self) -> None:
        """Synchronizes stack view, buttons visibility and indicator."""
        if self.headless:
            return

        if hasattr(self, "stack"):
            self.stack.set_visible_child_name(f"step_{self._current_step}")

        if hasattr(self, "step_label"):
            self.step_label.set_text(f"Passo {self._current_step} de {self.TOTAL_STEPS}")

        if hasattr(self, "back_button"):
            self.back_button.set_visible(self._current_step > 1)

        if hasattr(self, "next_button"):
            # Step 6 is the decision page with its own action cards
            self.next_button.set_visible(self._current_step < self.TOTAL_STEPS)

    def _load_css(self) -> None:
        """Injects custom CSS provider into GTK display."""
        try:
            display = Gdk.Display.get_default()
            if display:
                provider = Gtk.CssProvider()
                provider.load_from_data(COSMIC_CSS.encode("utf-8"))
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
        except Exception:
            pass


class LsdWelcomeApplication(Adw.Application if HAS_ADW else Gtk.Application):  # type: ignore
    """GTK4 / Libadwaita Application for LSD-Welcome."""

    def __init__(self) -> None:
        super().__init__(
            application_id="org.lsd_os.welcome",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.wizard: WelcomeWizard | None = None

    def do_activate(self) -> None:
        if not self.wizard:
            self.wizard = WelcomeWizard(headless=False, app=self)
        self.wizard.present()


def main() -> int:
    """CLI / Executable entry point."""
    if "--headless" in sys.argv:
        wizard = WelcomeWizard(headless=True)
        print(f"LSD-Welcome Headless initialized. Steps: {wizard.get_total_steps()}")
        return 0

    if HAS_ADW:
        Adw.init()

    app = LsdWelcomeApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
