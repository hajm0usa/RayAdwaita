from gi.repository import Adw
from gettext import gettext as _

class RayWelcomePage():
    """
    A Page that shown when there is no config save and
    helps user to add a conifg
    """

    def __init__(self, **kwargs):
        self.page = Adw.StatusPage()

        self.page.set_title(_("Welcome to RayAdwaita"))
        self.page.set_description(_("Add V2ray configs from the menu in top bar"))
        self.page.set_icon_name(_("ir.hajmousa.RayAdwaita"))
