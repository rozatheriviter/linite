#!/usr/bin/env python3
import sys
import json
import subprocess
import gi
import tempfile
import os
import stat

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class LiniteApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Linite - Pop!_OS App Installer")
        self.set_border_width(10)
        self.set_default_size(800, 600)

        # Load apps data
        try:
            with open('apps.json', 'r') as f:
                self.apps_data = json.load(f)
        except Exception as e:
            self.show_error(f"Failed to load apps.json: {e}")
            sys.exit(1)

        self.checkboxes = []

        # Main Layout
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_vbox)

        # Header
        header_label = Gtk.Label()
        header_label.set_markup("<big><b>Select apps to install</b></big>")
        main_vbox.pack_start(header_label, False, False, 10)

        # Scrolled Window for the list
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_vbox.pack_start(scrolled_window, True, True, 0)

        # Grid for categories
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scrolled_window.add(content_box)

        # Iterate categories
        for category, apps in self.apps_data.items():
            cat_frame = Gtk.Frame(label=category)
            content_box.pack_start(cat_frame, False, False, 5)

            cat_flow = Gtk.FlowBox()
            cat_flow.set_valign(Gtk.Align.START)
            cat_flow.set_max_children_per_line(3)
            cat_flow.set_selection_mode(Gtk.SelectionMode.NONE)
            cat_frame.add(cat_flow)

            for app in apps:
                # Create a box for check + label
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                check = Gtk.CheckButton()
                check.app_data = app # Store data in the widget
                self.checkboxes.append(check)

                label_text = f"<b>{app['name']}</b>\n<small>{app.get('description', '')}</small>"
                label = Gtk.Label()
                label.set_markup(label_text)
                label.set_xalign(0)

                hbox.pack_start(check, False, False, 0)
                hbox.pack_start(label, True, True, 0)

                # Tooltip
                hbox.set_tooltip_text(f"Install via {app['type']}: {app['id']}")

                cat_flow.add(hbox)

        # Bottom Action Bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_vbox.pack_start(action_box, False, False, 10)

        install_button = Gtk.Button(label="Install Selected")
        install_button.connect("clicked", self.on_install_clicked)
        install_button.get_style_context().add_class("suggested-action") # Blue button style
        action_box.pack_end(install_button, False, False, 0)

        select_all_btn = Gtk.Button(label="Select All")
        select_all_btn.connect("clicked", lambda w: self.toggle_all(True))
        action_box.pack_start(select_all_btn, False, False, 0)

        deselect_all_btn = Gtk.Button(label="Deselect All")
        deselect_all_btn.connect("clicked", lambda w: self.toggle_all(False))
        action_box.pack_start(deselect_all_btn, False, False, 0)

    def toggle_all(self, state):
        for check in self.checkboxes:
            check.set_active(state)

    def on_install_clicked(self, widget):
        to_install_apt = []
        to_install_flatpak = []

        for check in self.checkboxes:
            if check.get_active():
                app = check.app_data
                if app['type'] == 'apt':
                    to_install_apt.append(app['id'])
                elif app['type'] == 'flatpak':
                    to_install_flatpak.append(app['id'])

        if not to_install_apt and not to_install_flatpak:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No apps selected",
            )
            dialog.format_secondary_text("Please select at least one app to install.")
            dialog.run()
            dialog.destroy()
            return

        self.run_installation(to_install_apt, to_install_flatpak)

    def run_installation(self, apt_apps, flatpak_apps):
        # Construct the shell script content
        commands = ["#!/bin/bash"]
        commands.append("echo 'Starting installation...'")

        if apt_apps:
            commands.append("echo 'Updating apt repositories...'")
            commands.append("sudo apt update")
            apps_str = " ".join(apt_apps)
            commands.append(f"echo 'Installing apt packages: {apps_str}'")
            commands.append(f"sudo apt install -y {apps_str}")

        if flatpak_apps:
            apps_str = " ".join(flatpak_apps)
            commands.append(f"echo 'Installing flatpak packages: {apps_str}'")
            commands.append(f"flatpak install -y flathub {apps_str}")

        commands.append("echo 'Installation complete!'")
        commands.append("echo 'Press Enter to close this window.'")
        commands.append("read")

        script_content = "\n".join(commands)

        # Write to temporary file
        try:
            fd, script_path = tempfile.mkstemp(suffix=".sh", prefix="linite_install_")
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(script_content)

            # Make executable
            st = os.stat(script_path)
            os.chmod(script_path, st.st_mode | stat.S_IEXEC)
        except Exception as e:
            self.show_error(f"Failed to create temporary installation script: {e}")
            return

        # Try finding a terminal emulator
        terminals = ["cosmic-term", "gnome-terminal", "tilix", "x-terminal-emulator", "konsole", "xfce4-terminal"]
        terminal_cmd = None

        for term in terminals:
            if subprocess.call(["which", term], stdout=subprocess.DEVNULL) == 0:
                terminal_cmd = term
                break

        if terminal_cmd:
            try:
                if terminal_cmd == "cosmic-term":
                     subprocess.Popen([terminal_cmd, "--", "bash", "-c", script_path])
                elif terminal_cmd == "gnome-terminal":
                     subprocess.Popen([terminal_cmd, "--", "bash", "-c", script_path])
                else:
                     # Generic fallback
                     # Many terminals support -e "command" or -e command args
                     # Safe bet usually is -e "bash -c script"
                     subprocess.Popen([terminal_cmd, "-e", f"bash -c '{script_path}'"])
            except Exception as e:
                self.show_error(f"Failed to launch terminal {terminal_cmd}: {e}")
        else:
            self.show_error("No terminal emulator found. Cannot run installation.")

    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = LiniteApp()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
