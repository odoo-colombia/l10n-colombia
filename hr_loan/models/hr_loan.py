# Copyright 2021 Alejandro Olano <Github@alejo-code>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools.func import conditional
from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
            result['employee_id'] = self.env['hr.employee'].search(
                [('user_id', '=', ts_user_id)], limit=1).id
        return result

    @api.multi
    def _compute_loan_amount(self):
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

    name = fields.Char(string="Loan Name", default="/", readonly=True)
    date = fields.Date(string="Date",
                       default=fields.Date.today(),
                       readonly=True)
    employee_id = fields.Many2one(comodel_name='hr.employee',
                                  string="Employee",
                                  required=True)
    department_id = fields.Many2one(comodel_name='hr.department',
                                    related="employee_id.department_id",
                                    readonly=True,
                                    string="Department")
    installment = fields.Integer(string="No Of Installments", default=1)
    payment_date = fields.Date(string="Payment Start Date",
                               required=True,
                               default=fields.Date.today())
    loan_lines = fields.One2many(comodel_name='hr.loan.line',
                                 inverse_name='loan_id',
                                 string="Loan Line",
                                 index=True)
    emp_account_id = fields.Many2one(comodel_name='account.account',
                                     string="Loan Account")
    treasury_account_id = fields.Many2one(comodel_name='account.account',
                                          string="Treasury Account")
    journal_id = fields.Many2one(comodel_name='account.journal',
                                 string="Journal")
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    job_position = fields.Many2one(comodel_name='hr.job',
                                   related="employee_id.job_id",
                                   readonly=True,
                                   string="Job Position")
    loan_amount = fields.Float(string="Loan Amount", required=True)
    total_amount = fields.Float(string="Total Amount",
                                readonly=True,
                                store=True,
                                compute='_compute_loan_amount')
    balance_amount = fields.Float(string="Balance Amount",
                                  store=True,
                                  compute='_compute_loan_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount",
                                     store=True,
                                     compute='_compute_loan_amount')

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('waiting_approval_1', 'Submitted'),
            ('waiting_approval_2', 'Waiting Approval'),
            ('approve', 'Approved'),
            ('refuse', 'Refused'),
            ('cancel', 'Canceled'),
        ],
        string="State",
        default='draft',
        track_visibility='onchange',
        copy=False,
    )

    @api.model
    def create(self, values):
        loan_count = self.env['hr.loan'].search_count([
            ('employee_id', '=', values['employee_id']),
            ('state', '=', 'approve'), ('balance_amount', '!=', 0)
        ])
        if loan_count:
            raise ValidationError(
                _("The employee has already a pending installment"))
        else:
            values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
            res = super(HrLoan, self).create(values)
            return res

    @api.multi
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    @api.multi
    def action_submit(self):
        self.write({'state': 'waiting_approval_1'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_approve(self):
        for data in self:
            contract_obj = self.env['hr.contract'].search(
                [('employee_id', '=', data.employee_id.id),
                 ('state', '=', 'open')],
                limit=1)
            if not contract_obj:
                raise UserError(_('You must Define a contract for employee.'))
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'approve'})

    @api.multi
    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete a loan which is not in draft or cancelled state'
                )
        return super(HrLoan, self).unlink()

    @api.multi
    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date':
                    date_start,
                    'amount':
                    amount,
                    'employee_id':
                    loan.employee_id.id,
                    'loan_id':
                    loan.id
                })
                #Febrero
                nb_of_days = 0
                if date_start.month == 2 and date_start.day >= 15:
                    nb_of_days = 2
                    if ((date_start.year % 4 == 0
                         and date_start.year % 100 != 0)
                            or date_start.year % 400 == 0):
                        if date_start.day >= 15:
                            nb_of_days = 1
                    if date_start.month == 2 and date_start.day == 28 or date_start.day == 29:
                        nb_of_days = 0

                if date_start.day == 30:
                    nb_of_days = -1

                date_start2 = date_start + relativedelta(
                    days=15) - relativedelta(days=nb_of_days)
                if date_start2.day == 16:
                    date_start2 = date_start + relativedelta(
                        days=15) - relativedelta(
                            days=nb_of_days) - relativedelta(days=1)

                date_start = date_start2

            loan._compute_loan_amount()
        return True


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee',
                                  string="Employee")
    amount = fields.Float(string="Amount", required=True)
    paid = fields.Boolean(string="Paid")
    loan_id = fields.Many2one(comodel_name='hr.loan', string="Loan Ref.")
    payslip_id = fields.Many2one(comodel_name='hr.payslip',
                                 string="Payslip Ref.")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.one
    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id',
                                                             '=', self.id)])

    loan_count = fields.Integer(string="Loan Count",
                                compute='_compute_employee_loans')
