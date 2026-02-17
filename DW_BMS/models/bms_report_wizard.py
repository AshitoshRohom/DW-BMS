import base64
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import xlsxwriter
from odoo import fields, models


class BmsReportWizard(models.TransientModel):
    _name = "bms.report.wizard"
    _description = "BMS Consolidated Report Wizard"

    partner_id = fields.Many2one("res.partner", string="Customer")
    user_id = fields.Many2one("res.users", string="Salesperson")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    payment_status = fields.Selection(
        [
            ("all", "All"),
            ("paid", "Paid"),
            ("partial", "Partially Paid"),
            ("not_paid", "Not Paid"),
        ],
        default="all",
    )
    shipping_status = fields.Selection(
        [("all", "All"), ("done", "Delivered"), ("pending", "Pending")],
        default="all",
    )

    xlsx_file = fields.Binary(readonly=True)
    xlsx_filename = fields.Char(readonly=True)

    def _date_domain(self, field_name):
        domain = []
        if self.date_from:
            domain.append((field_name, ">=", self.date_from))
        if self.date_to:
            domain.append((field_name, "<=", self.date_to))
        return domain

    def _payment_status_domain(self):
        if self.payment_status == "all":
            return []
        if self.payment_status == "paid":
            return [("payment_state", "=", "paid")]
        if self.payment_status == "partial":
            return [("payment_state", "=", "partial")]
        return [("payment_state", "in", ("not_paid", "in_payment"))]

    def _shipping_domain(self):
        if self.shipping_status == "all":
            return []
        if "picking_ids" not in self.env["sale.order"]._fields:
            return []
        if self.shipping_status == "done":
            return [("picking_ids.state", "=", "done")]
        return [("picking_ids.state", "not in", ("done", "cancel"))]

    def _collect_data(self):
        self.ensure_one()

        sale_domain = [("state", "in", ("sale", "done"))]
        purchase_domain = [("state", "in", ("purchase", "done"))]
        invoice_domain = [("move_type", "in", ("out_invoice", "in_invoice")), ("state", "=", "posted")]
        payment_domain = [("state", "=", "posted")]

        sale_domain += self._date_domain("date_order")
        purchase_domain += self._date_domain("date_order")
        invoice_domain += self._date_domain("invoice_date")
        payment_domain += self._date_domain("date")

        if self.partner_id:
            sale_domain.append(("partner_id", "=", self.partner_id.id))
            purchase_domain.append(("partner_id", "=", self.partner_id.id))
            invoice_domain.append(("partner_id", "=", self.partner_id.id))
            payment_domain.append(("partner_id", "=", self.partner_id.id))

        if self.user_id:
            sale_domain.append(("user_id", "=", self.user_id.id))

        sale_domain += self._shipping_domain()
        invoice_domain += self._payment_status_domain()

        sale_orders = self.env["sale.order"].search(sale_domain)
        purchase_orders = self.env["purchase.order"].search(purchase_domain)
        invoices = self.env["account.move"].search(invoice_domain)
        payments = self.env["account.payment"].search(payment_domain)

        sale_by_user = defaultdict(float)
        for order in sale_orders:
            sale_by_user[order.user_id.name or "Undefined"] += order.amount_total

        stock_lines = []
        for product in self.env["product.product"].search([("type", "=", "product")]):
            if not product.qty_available:
                continue
            stock_lines.append(
                {
                    "product": product.display_name,
                    "qty": product.qty_available,
                    "value": product.qty_available * product.standard_price,
                }
            )

        bank_summary = defaultdict(float)
        for payment in payments:
            bank_name = payment.journal_id.name or "Undefined"
            bank_summary[bank_name] += payment.amount

        payment_pending = sum(
            invoices.filtered(lambda move: move.payment_state != "paid").mapped("amount_residual")
        )

        return {
            "generated_on": datetime.now(),
            "filters": {
                "partner": self.partner_id.display_name or "All",
                "payment_status": dict(self._fields["payment_status"].selection).get(self.payment_status),
                "date_from": self.date_from,
                "date_to": self.date_to,
                "user": self.user_id.display_name or "All",
                "shipping_status": dict(self._fields["shipping_status"].selection).get(self.shipping_status),
            },
            "sale_total": sum(sale_by_user.values()),
            "sale_by_user": [{"user": user, "amount": amount} for user, amount in sale_by_user.items()],
            "purchase_total": sum(purchase_orders.mapped("amount_total")),
            "stock_total_qty": sum(line["qty"] for line in stock_lines),
            "stock_total_value": sum(line["value"] for line in stock_lines),
            "stock_lines": stock_lines,
            "payment_pending": payment_pending,
            "bank_lines": [{"bank": bank, "amount": amount} for bank, amount in bank_summary.items()],
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref("DW_BMS.action_bms_summary_pdf").report_action(self)

    def action_generate_xlsx(self):
        self.ensure_one()
        data = self._collect_data()

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("BMS Report")
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})

        row = 0
        sheet.write(row, 0, "BMS Consolidated Report", bold)
        row += 2

        sheet.write(row, 0, "Total Sales", bold)
        sheet.write(row, 1, data["sale_total"], money)
        row += 1
        sheet.write(row, 0, "Total Purchase", bold)
        sheet.write(row, 1, data["purchase_total"], money)
        row += 1
        sheet.write(row, 0, "Payment Pending", bold)
        sheet.write(row, 1, data["payment_pending"], money)
        row += 2

        sheet.write(row, 0, "Total Sale by User", bold)
        row += 1
        sheet.write(row, 0, "User", bold)
        sheet.write(row, 1, "Amount", bold)
        row += 1
        for line in data["sale_by_user"]:
            sheet.write(row, 0, line["user"])
            sheet.write(row, 1, line["amount"], money)
            row += 1

        row += 1
        sheet.write(row, 0, "Bank Summary", bold)
        row += 1
        sheet.write(row, 0, "Bank", bold)
        sheet.write(row, 1, "Amount", bold)
        row += 1
        for line in data["bank_lines"]:
            sheet.write(row, 0, line["bank"])
            sheet.write(row, 1, line["amount"], money)
            row += 1

        row += 1
        sheet.write(row, 0, "Stock", bold)
        row += 1
        sheet.write(row, 0, "Product", bold)
        sheet.write(row, 1, "Qty", bold)
        sheet.write(row, 2, "Value", bold)
        row += 1
        for line in data["stock_lines"]:
            sheet.write(row, 0, line["product"])
            sheet.write(row, 1, line["qty"])
            sheet.write(row, 2, line["value"], money)
            row += 1

        workbook.close()
        file_data = base64.b64encode(output.getvalue())
        filename = f"bms_report_{fields.Date.today()}.xlsx"
        self.write({"xlsx_file": file_data, "xlsx_filename": filename})

        return {
            "type": "ir.actions.act_window",
            "res_model": "bms.report.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
