from odoo import api, fields, models


class HomeDashboard(models.Model):
    _name = "home.dashboard"
    _description = "Home Dashboard"

    name = fields.Char(default="Home Dashboard", readonly=True)

    # User panel (current user only)
    user_total_sale = fields.Monetary(string="Total Sale (User)", compute="_compute_kpis", currency_field="currency_id")
    user_total_purchase = fields.Monetary(string="Total Purchase (User)", compute="_compute_kpis", currency_field="currency_id")
    user_sale_payment_due = fields.Monetary(string="Sale Payment Due (User)", compute="_compute_kpis", currency_field="currency_id")
    user_purchase_payment_due = fields.Monetary(string="Purchase Payment Due (User)", compute="_compute_kpis", currency_field="currency_id")
    user_stock_alert_ordered = fields.Integer(string="Products Stock Alert (User)", compute="_compute_kpis")
    user_pending_shipment = fields.Integer(string="Pending Shipment (User)", compute="_compute_kpis")
    user_pending_job_work = fields.Integer(string="Pending Job Work (User)", compute="_compute_kpis")

    # Admin panel (all data)
    admin_total_sale = fields.Monetary(string="Total Sale (All)", compute="_compute_kpis", currency_field="currency_id")
    admin_total_purchase = fields.Monetary(string="Total Purchase (All)", compute="_compute_kpis", currency_field="currency_id")
    admin_sale_payment_due = fields.Monetary(string="Sale Payment Due (All)", compute="_compute_kpis", currency_field="currency_id")
    admin_purchase_payment_due = fields.Monetary(string="Purchase Payment Due (All)", compute="_compute_kpis", currency_field="currency_id")
    admin_stock_alert_ordered = fields.Integer(string="Products Stock Alert (All)", compute="_compute_kpis")
    admin_pending_shipment = fields.Integer(string="Pending Shipment (All)", compute="_compute_kpis")
    admin_pending_job_work = fields.Integer(string="Pending Job Work (All)", compute="_compute_kpis")

    currency_id = fields.Many2one("res.currency", compute="_compute_currency", store=False)

    @api.depends_context("allowed_company_ids", "uid")
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = self.env.company.currency_id

    def _company_domain(self):
        company_ids = self.env.companies.ids
        return [("company_id", "in", company_ids)]

    def _due_domain(self, move_type):
        return [
            ("move_type", "=", move_type),
            ("state", "=", "posted"),
            ("payment_state", "not in", ["paid", "reversed", "invoicing_legacy"]),
        ]

    def _sum_amount(self, model_name, domain, field_name="amount_total"):
        groups = self.env[model_name].read_group(domain, [field_name], [])
        return groups and groups[0].get(field_name) or 0.0

    def _count_records(self, model_name, domain):
        return self.env[model_name].search_count(domain)

    def _pending_job_work_count(self, scope="all"):
        # Prefer custom Job Work model if available, otherwise fallback to Manufacturing Orders.
        if "job.work" in self.env:
            job_domain = [("state", "not in", ["done", "cancel"])]
            if scope == "user":
                job_model = self.env["job.work"]
                if "user_id" in job_model._fields:
                    job_domain.append(("user_id", "=", self.env.user.id))
                elif "create_uid" in job_model._fields:
                    job_domain.append(("create_uid", "=", self.env.user.id))
            return self._count_records("job.work", job_domain)

        mo_model = self.env["mrp.production"]
        mo_domain = self._company_domain() + [("state", "not in", ["done", "cancel"])]
        if scope == "user":
            if "user_id" in mo_model._fields:
                mo_domain.append(("user_id", "=", self.env.user.id))
            else:
                mo_domain.append(("create_uid", "=", self.env.user.id))
        return self._count_records("mrp.production", mo_domain)

    @api.depends_context("allowed_company_ids", "uid")
    def _compute_kpis(self):
        user = self.env.user

        company_domain = self._company_domain()

        # Admin / All panel
        admin_sale_domain = company_domain + [("state", "in", ["sale", "done"])]
        admin_purchase_domain = company_domain + [("state", "in", ["purchase", "done"])]
        admin_sale_due_domain = company_domain + self._due_domain("out_invoice")
        admin_purchase_due_domain = company_domain + self._due_domain("in_invoice")
        admin_orderpoint_domain = company_domain + [("qty_to_order", ">", 0)]
        admin_shipment_domain = company_domain + [
            ("picking_type_code", "=", "outgoing"),
            ("state", "not in", ["done", "cancel"]),
        ]

        # User panel
        user_sale_domain = company_domain + [
            ("state", "in", ["sale", "done"]),
            ("user_id", "=", user.id),
        ]
        user_purchase_domain = company_domain + [
            ("state", "in", ["purchase", "done"]),
            ("user_id", "=", user.id),
        ]
        user_sale_due_domain = company_domain + self._due_domain("out_invoice") + [
            "|", ("invoice_user_id", "=", user.id), ("create_uid", "=", user.id),
        ]
        user_purchase_due_domain = company_domain + self._due_domain("in_invoice") + [
            "|", ("invoice_user_id", "=", user.id), ("create_uid", "=", user.id),
        ]
        user_orderpoint_domain = company_domain + [("qty_to_order", ">", 0), ("create_uid", "=", user.id)]
        user_shipment_domain = company_domain + [
            ("picking_type_code", "=", "outgoing"),
            ("state", "not in", ["done", "cancel"]),
            "|", ("user_id", "=", user.id), ("create_uid", "=", user.id),
        ]

        for rec in self:
            rec.admin_total_sale = self._sum_amount("sale.order", admin_sale_domain, "amount_total")
            rec.admin_total_purchase = self._sum_amount("purchase.order", admin_purchase_domain, "amount_total")
            rec.admin_sale_payment_due = self._sum_amount("account.move", admin_sale_due_domain, "amount_residual")
            rec.admin_purchase_payment_due = self._sum_amount("account.move", admin_purchase_due_domain, "amount_residual")
            rec.admin_stock_alert_ordered = self._count_records("stock.warehouse.orderpoint", admin_orderpoint_domain)
            rec.admin_pending_shipment = self._count_records("stock.picking", admin_shipment_domain)
            rec.admin_pending_job_work = self._pending_job_work_count("all")

            rec.user_total_sale = self._sum_amount("sale.order", user_sale_domain, "amount_total")
            rec.user_total_purchase = self._sum_amount("purchase.order", user_purchase_domain, "amount_total")
            rec.user_sale_payment_due = self._sum_amount("account.move", user_sale_due_domain, "amount_residual")
            rec.user_purchase_payment_due = self._sum_amount("account.move", user_purchase_due_domain, "amount_residual")
            rec.user_stock_alert_ordered = self._count_records("stock.warehouse.orderpoint", user_orderpoint_domain)
            rec.user_pending_shipment = self._count_records("stock.picking", user_shipment_domain)
            rec.user_pending_job_work = self._pending_job_work_count("user")

    def action_refresh_dashboard(self):
        return {"type": "ir.actions.client", "tag": "reload"}
