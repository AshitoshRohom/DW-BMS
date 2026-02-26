from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    stock_qty = fields.Float(
        string="Stock",
        compute="_compute_stock_qty",
        store=False,
    )

    @api.depends("product_id")
    def _compute_stock_qty(self):
        for line in self:
            if line.product_id:
                line.stock_qty = line.product_id.with_context(
                    warehouse=line.order_id.warehouse_id.id
                ).qty_available
            else:
                line.stock_qty = 0.0

    @api.constrains("price_unit", "discount", "product_id")
    def _check_price_unit_not_decreased(self):
        for line in self:
            if not line.product_id or line.display_type:
                continue

            min_allowed_price = line.product_id.product_tmpl_id.min_sale_price or line.product_id.list_price
            effective_unit_price = (line.price_unit or 0.0) * (1.0 - (line.discount or 0.0) / 100.0)
            rounding = line.order_id.currency_id.rounding or 0.01

            if float_compare(effective_unit_price, min_allowed_price, precision_rounding=rounding) < 0:
                raise ValidationError(
                    "Effective Unit Price cannot be less than the minimum allowed selling price.\n"
                    "Product: %s\n"
                    "Minimum allowed price: %.2f\n"
                    "Entered unit price: %.2f\n"
                    "Discount: %.2f%%\n"
                    "Effective unit price: %.2f"
                    % (
                        line.product_id.display_name,
                        min_allowed_price,
                        line.price_unit,
                        line.discount or 0.0,
                        effective_unit_price,
                    )
                )


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
