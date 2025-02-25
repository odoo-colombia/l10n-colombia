# -*- coding: utf-8 -*-
# Copyright 2021 Alejandro Olano <Github@alejo-code>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    invoice_type_code = fields.Selection(
        selection_add=[('02', _('E-invoice of sale - exportation'))])
