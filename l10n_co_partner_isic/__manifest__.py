# -*- coding: utf-8 -*-
# Copyright 2018 Joan Marín <Github@JoanMarin>
# Copyright 2018 Guillermo Montoya <Github@guillermm>
# Copyright 2021 Alejandro Olano <Github@alejo-code>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name":
    "Partner ISIC Codes",
    "summary":
    "ISIC Codes - Classification of Economic Activities ISIC",
    "version":
    "12.0.1.0.0",
    "license":
    "AGPL-3",
    "website":
    "https://github.com/odooloco/l10n-colombia",
    "author":
    "EXA Auto Parts Github@exaap, "
    "Alejandro Olano Github@alejo-code, "
    "Joan Marín Github@JoanMarin, "
    "Guillermo Montoya Github@guillermm",
    "category":
    "Localization",
    "depends": ["base", "account"],
    "data": [
        "security/ir.model.access.csv", "data/res.partner.isic.csv",
        "views/res_partner_isic_views.xml", "views/res_partner_views.xml"
    ],
    "installable":
    True,
}
