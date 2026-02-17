from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_products_weight = fields.Float(
        string="Total Products Weight",
        compute="_compute_total_products_weight",
        store=True,
    )

    @api.depends("order_line.product_id.weight", "order_line.product_uom_qty", "order_line.display_type")
    def _compute_total_products_weight(self):
        for order in self:
            order.total_products_weight = sum(
                (line.product_id.weight or 0.0) * line.product_uom_qty
                for line in order.order_line
                if not line.display_type
            )
