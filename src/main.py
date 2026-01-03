# main.py
#
# Copyright 2026 HajMousa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import RayadwaitaWindow


class RayadwaitaApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id='ir.hajmousa.RayAdwaita',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/ir/hajmousa/RayAdwaita')
        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = RayadwaitaWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(application_name='rayadwaita',
                                application_icon='ir.hajmousa.RayAdwaita',
                                developer_name='HajMousa',
                                version='0.1.0',
                                issue_url="https://github.com/hajm0usa/RayAdwaita/issues",
                                developers=['HajMousa'],
                                copyright='© 2026 HajMousa')
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_('translator-credits'))
        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    app = RayadwaitaApplication()
    return app.run(sys.argv)
