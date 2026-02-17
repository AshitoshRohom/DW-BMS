from odoo import models, fields, api
from datetime import date


class DwHomeDashboard(models.Model):
    _name = 'dw.home.dashboard'
    _description = 'DW Home Dashboard'
    _rec_name = 'id'

    # ========================
    # KPI Fields
    # ========================
    total_sale = fields.Float(string="Total Sales", compute="_compute_data")
    total_purchase = fields.Float(string="Total Purchase", compute="_compute_data")
    sale_due = fields.Float(string="Sale Payment Due", compute="_compute_data")
    purchase_due = fields.Float(string="Purchase Payment Due", compute="_compute_data")

    # ========================
    # Alert Fields
    # ========================
    low_stock_count = fields.Integer(string="Low Stock Products", compute="_compute_data")
    pending_shipment_count = fields.Integer(string="Pending Shipments", compute="_compute_data")
    pending_job_count = fields.Integer(string="Pending Job Work", compute="_compute_data")
    overdue_invoice_count = fields.Integer(string="Overdue Customer Invoices", compute="_compute_data")
    overdue_bill_count = fields.Integer(string="Overdue Vendor Bills", compute="_compute_data")

    # ========================
    # Auto Create Single Record
    # ========================
    @api.model
    def create_dashboard_record(self):
        record = self.search([], limit=1)
        if not record:
            record = self.create({})
        return record

    # ========================
    # Compute Data
    # ========================
    @api.depends()
    def _compute_data(self):
        for rec in self:
            user = self.env.user
            is_admin = user.has_group('base.group_system')

            sale_domain = []
            purchase_domain = []
            picking_domain = []

            if not is_admin:
                sale_domain = [('user_id', '=', user.id)]
                purchase_domain = [('user_id', '=', user.id)]
                picking_domain = [('user_id', '=', user.id)]

            # Total Sales
            sales = self.env['sale.order'].search(
                sale_domain + [('state', 'in', ['sale', 'done'])]
            )
            rec.total_sale = sum(sales.mapped('amount_total'))

            # Total Purchase
            purchases = self.env['purchase.order'].search(
                purchase_domain + [('state', 'in', ['purchase', 'done'])]
            )
            rec.total_purchase = sum(purchases.mapped('amount_total'))

            # Sale Due
            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ])
            rec.sale_due = sum(invoices.mapped('amount_residual'))

            # Purchase Due
            bills = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ])
            rec.purchase_due = sum(bills.mapped('amount_residual'))

            # Low Stock (<= 5)
            low_stock = self.env['product.product'].search([
                ('qty_available', '<=', 5)
            ])
            rec.low_stock_count = len(low_stock)

            # Pending Shipments
            pending_pickings = self.env['stock.picking'].search(
                picking_domain + [('state', 'not in', ['done', 'cancel'])]
            )
            rec.pending_shipment_count = len(pending_pickings)

            # Pending Job Work
            jobs = self.env['mrp.production'].search([
                ('state', 'not in', ['done', 'cancel'])
            ])
            rec.pending_job_count = len(jobs)

            today = date.today()

            # Overdue Customer Invoices
            overdue_inv = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])
            rec.overdue_invoice_count = len(overdue_inv)

            # Overdue Vendor Bills
            overdue_bill = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date_due', '<', today),
                ('payment_state', '!=', 'paid')
            ])
            rec.overdue_bill_count = len(overdue_bill)


    @api.model
    def create(self, vals):
        record = super().create(vals)
        return record

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.search([], limit=1):
            self.create({})
        return res
