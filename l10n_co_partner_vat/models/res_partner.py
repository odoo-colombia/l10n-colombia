# -*- coding: utf-8 -*-
# Copyright 2018 Joan Marín <Github@JoanMarin>
# Copyright 2018 Guillermo Montoya <Github@guillermm>
# Copyright 2021 Alejandro Olano <Github@alejo-code>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    document_type_id = fields.Many2one(
        string='Document Type', comodel_name='res.partner.document.type')
    document_type_code = fields.Char(related='document_type_id.code',
                                     store=False)
    check_digit = fields.Char(string='Verification Digit', size=1)
    identification_document = fields.Char(string='Identification Document')

    @api.onchange('country_id', 'identification_document', 'check_digit',
                  'document_type_id')
    def _onchange_vat(self):
        if self.country_id and self.identification_document:
            if self.country_id.code:
                if self.check_digit and self.document_type_code == '31':
                    self.vat = self.country_id.code + self.identification_document + self.check_digit
                elif self.document_type_code == '43':
                    self.check_digit = False
                    self.vat = 'CO' + self.identification_document
                else:
                    self.check_digit = False
                    self.vat = self.country_id.code + self.identification_document
            else:
                msg = _('The Country has No ISO Code.')
                raise ValidationError(msg)
        elif not self.identification_document and self.vat:
            self.vat = False

    @api.constrains('vat', 'document_type_id', 'country_id')
    def check_vat(self):
        def _checking_required(partner):
            '''
            Este método solo aplica para Colombia y obliga a seleccionar
            un tipo de documento de identidad con el fin de determinar
            si es verificable por el algoritmo VAT. Si no se define,
            de todas formas el VAT se evalua como un NIT.
            '''
            return ((partner.document_type_id
                     and partner.document_type_id.checking_required)
                    or (not partner.parent_id
                        and not partner.document_type_id)) == True

        msg = _('The Identification Document does not seems to be correct.')

        for partner in self:
            if not partner.vat:
                continue

            vat_country, vat_number = partner._split_vat(partner.vat)

            if partner.document_type_code == '43':
                vat_country = 'co'
            elif partner.country_id:
                vat_country = partner.country_id.code.lower()

            if not hasattr(partner, 'check_vat_' + vat_country):
                continue

            check = getattr(partner, 'check_vat_' + vat_country)

            if vat_country == 'co':
                if not _checking_required(partner):
                    continue

            if check and not check(vat_number):
                raise ValidationError(msg)

        return True

    def check_vat_co(self, vat):
        '''
        Check VAT Routine for Colombia.
        '''
        if type(vat) == str:
            vat = vat.replace('-', '', 1).replace('.', '', 2)

        if len(str(vat)) < 4:
            return False

        try:
            int(vat)
        except ValueError:
            return False

        # Validación Sin identificación del exterior
        # o para uso definido por la DIAN
        if len(str(vat)) == 9 and str(vat)[0:5] == '44444' \
            and int(str(vat)[5:]) <= 9000 \
            and int(str(vat)[5:]) >= 4001:

            return True

        prime = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        sum = 0
        vat_len = len(str(vat))

        for i in range(vat_len - 2, -1, -1):
            sum += int(str(vat)[i]) * prime[vat_len - 2 - i]

        if sum % 11 > 1:
            return str(vat)[vat_len - 1] == str(11 - (sum % 11))
        else:
            return str(vat)[vat_len - 1] == str(sum % 11)

    def _compute_check_digit(self):
        prime = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]

        if not self.identification_document:
            return False

        check_digit = 0
        identification_document = self.identification_document.strip()

        for i, character in enumerate(identification_document[::-1]):
            try:
                digit = int(character)
            except:
                return False

            check_digit += digit * prime[i]

        check_digit %= 11
        check_digit = check_digit if check_digit >= 0 else 0
        check_digit = (11 - check_digit) if check_digit >= 2 else check_digit

        return check_digit
