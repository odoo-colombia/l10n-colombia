# -*- coding: utf-8 -*-
# Copyright 2016 Dominic Krimmer
# Copyright 2016 Luis Alfredo da Silva (luis.adasilvaf@gmail.com)
# Copyright 2019 Joan Marín <Github@JoanMarin>
# Copyright 2021 Alejandro Olano <Github@alejo-code>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz
from dateutil import tz
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    use_dian_control = fields.Boolean(string='Use DIAN Resolutions Control?')
    remaining_numbers = fields.Integer(string='Remaining Numbers', default=False)
    remaining_days = fields.Integer(string='Remaining Days', default=False)
    dian_type = fields.Selection(
        selection=[
            ('computer_generated_invoice', 'Computer Generated Invoice'),
            ('paper_invoice', 'Paper Invoice'),
            ('pos_invoice', 'POS Invoice')],
        string='DIAN Type')
    description = fields.Text(string='Resolution Description')

    @api.model
    def create(self, vals):
        rec = super(IrSequence, self).create(vals)

        for sequence_id in rec:
            if sequence_id.use_dian_control:
                sequence_id.check_active_resolution()

            sequence_id.check_date_range_ids()

        return rec

    @api.multi
    def write(self, vals):
        res = super(IrSequence, self).write(vals)

        for sequence_id in self:
            if sequence_id.use_dian_control:
                sequence_id.check_active_resolution()

            sequence_id.check_date_range_ids()

        return res

    @api.onchange('use_dian_control')
    def onchange_active_resolution(self):
        for sequence_id in self:
            sequence_id.use_date_range = True

    @api.multi
    def check_active_resolution(self):
        msg1 = _('Final Date - Resolution, must be greater or equal than Final Date.')

        if self.use_dian_control:
            if self.implementation != 'no_gap':
                self.implementation = 'no_gap'

            if self.padding != 0:
                self.padding = 0

            if not self.use_date_range:
                self.use_date_range = True

            if self.suffix:
                self.suffix = False

            if self.number_increment != 1:
                self.number_increment = 1

            timezone = pytz.timezone(self.env.user.tz or 'America/Bogota')
            from_zone = tz.gettz('UTC')
            to_zone = tz.gettz(timezone.zone)
            current_date = datetime.now().replace(tzinfo=from_zone)
            current_date = current_date.astimezone(to_zone).strftime('%Y-%m-%d')

            for date_range_id in self.date_range_ids:
                number_next_actual = date_range_id.number_next_actual
                date_from = datetime.strftime(date_range_id.date_from, '%Y-%m-%d')
                date_to = datetime.strftime(date_range_id.date_to, '%Y-%m-%d')
                date_to_resolution = datetime.strftime(
                    date_range_id.date_to_resolution, '%Y-%m-%d')

                if date_to_resolution < date_to:
                    raise ValidationError(msg1)

                if (number_next_actual >= date_range_id.number_from
                        and number_next_actual <= date_range_id.number_to
                        and current_date >= date_from
                        and current_date <= date_to):
                    if not date_range_id.active_resolution:
                        date_range_id.active_resolution = True

                    if date_range_id.prefix != self.prefix:
                        date_range_id.prefix = self.prefix
                else:
                    date_range_id.active_resolution = False

                if not date_range_id.prefix:
                    date_range_id.prefix = self.prefix

        return True

    def check_date_range_ids(self):
        msg1 = _('Final Date must be greater or equal than Initial Date.')
        msg2 = _('The Date Range must be unique or a date ' +
                 'must not be included in another Date Range.')
        msg3 = _('Number To must be greater or equal than Number From.')
        msg4 = _('The Number Next must be greater in one to Number To, to represent '
                 'a finished sequence or Number Next must be included in Number Range.')
        msg5 = _('The system needs only one active DIAN resolution.')
        msg6 = _('The system needs at least one active DIAN resolution.')
        date_ranges = []
        _active_resolution = 0

        for date_range_id in self.date_range_ids:
            if date_range_id.date_from and date_range_id.date_to:
                if date_range_id.date_from > date_range_id.date_to:
                    raise ValidationError(msg1)

                date_ranges.append((date_range_id.date_from, date_range_id.date_to))
                date_ranges.sort(key=lambda date_range: date_range[0])
                date_from = False
                date_to = False

                for date_range in date_ranges:
                    if not date_from and not date_to:
                        date_from = date_range[0]
                        date_to = date_range[1]
                        continue

                    if date_to < date_range[0]:
                        date_from = date_range[0]
                        date_to = date_range[1]
                    else:
                        raise ValidationError(msg2)

            if date_range_id.number_from and date_range_id.number_to:
                if date_range_id.number_from > date_range_id.number_to:
                    raise ValidationError(msg3)
                elif (date_range_id.number_next_actual >
                      (date_range_id.number_to + 1)
                      or date_range_id.number_from >
                      date_range_id.number_next_actual):
                    raise ValidationError(msg4)

            if date_range_id.active_resolution and self.use_dian_control:
                _active_resolution += 1

        if self.use_dian_control:
            if _active_resolution > 1:
                raise ValidationError(msg5)

            if _active_resolution == 0:
                raise ValidationError(msg6)

    def _next(self):
        msg = _('There is no active authorized invoicing resolution.')
        date_range_ids = self.date_range_ids.filtered(lambda dr: dr.active_resolution)

        if self.use_dian_control and not date_range_ids:
            raise ValidationError(msg)

        res = super(IrSequence, self)._next()

        if self.use_dian_control:
            self.check_active_resolution()

        return res
