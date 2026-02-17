from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    min_alert_qty = fields.Float(
        string="Minimum Order Quantity",
        default=5.0,
        help="If On Hand Quantity goes below this value, product will be marked as Low Stock.",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    min_alert_qty = fields.Float(
        related="product_tmpl_id.min_alert_qty",
        readonly=False,
    )

    alert_status = fields.Selection(
        [
            ("normal", "Normal"),
            ("low", "Low Stock"),
        ],
        string="Alert Status",
        compute="_compute_alert_status",
    )

    is_low_stock = fields.Boolean(
        string="Low Stock",
        compute="_compute_alert_status",
        search="_search_low_stock",
    )

    @api.depends("qty_available", "min_alert_qty", "type")
    def _compute_alert_status(self):
        for product in self:
            if product.type == "product" and product.qty_available < (product.min_alert_qty or 0.0):
                product.alert_status = "low"
                product.is_low_stock = True
            else:
                product.alert_status = "normal"
                product.is_low_stock = False

    def _search_low_stock(self, operator, value):
        if operator not in ['=', '!=']:
            raise NotImplementedError(_('Operation %s not implemented.') % (operator))
        
        # We need to find products where qty_available < min_alert_qty
        # Since we can't search on computed non-stored fields directly in SQL easily without stored dependent fields,
        # and qty_available is computed (but stored if not using specific locations),
        # A pure SQL search for "qty_available < min_alert_qty" is tricky because qty_available is computed.
        # However, for the user requirement "Low Stock Products" menu, we can iterate or use a domain if possible.
        # But for performance on large databases, python-side filtering is slow.
        # Given this is likely a small-to-medium DB, we can try searching.
        
        # Domain to find IDs:
        # 1. Get all products with type 'product'
        # 2. Filter them in python (slow but accurate for computed qtys)
        # OR use a specific domain if stock levels are stored.
        
        # Let's use a python filter for now as it's safest for correctness with complex stock logic.
        
        products = self.search([('type', '=', 'product')])
        low_stock_ids = []
        for product in products:
            if product.qty_available < (product.min_alert_qty or 0.0):
                low_stock_ids.append(product.id)
                
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('id', 'in', low_stock_ids)]
        else:
            return [('id', 'not in', low_stock_ids)]

