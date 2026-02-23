from odoo import _, fields, models
from odoo.tools.float_utils import float_compare


class ProductTemplate(models.Model):
    _inherit = "product.template"

    detailed_type = fields.Selection(default="product")

    min_sale_price = fields.Float(
        string="Min Sale Price",
        help="Minimum allowed selling price used for validation or reference.",
    )
    
    product_storage_location = fields.Char(
        string="Product Locations",
        help="Text field to describe where the product is stored (e.g. Shelf A, Bin 3).",
    )
    
    opening_stock_ref = fields.Float(
        string="Opening Stock (Reference)",
        help="Reference field for imported opening stock.",
    )

    opening_stock_added_qty = fields.Float(
        string="Opening Stock Added Qty",
        default=0.0,
        readonly=True,
        copy=False,
    )

    opening_stock_pending_qty = fields.Float(
        string="Pending Opening Qty",
        compute="_compute_opening_stock_pending_qty",
    )
    
    unit_value = fields.Integer(
        string="Unit",
        default=1,
        help="Integer unit value for product.",
    )

    def _compute_opening_stock_pending_qty(self):
        for product_tmpl in self:
            pending_qty = (product_tmpl.opening_stock_ref or 0.0) - (product_tmpl.opening_stock_added_qty or 0.0)
            product_tmpl.opening_stock_pending_qty = max(pending_qty, 0.0)

    def _create_opening_stock_moves(self, qty_map):
        inventory_location = self.env.ref("stock.stock_location_inventory", raise_if_not_found=False)
        stock_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if not inventory_location or not stock_location:
            return

        move_vals_list = []
        for product_tmpl, opening_qty in qty_map.items():
            if opening_qty <= 0:
                continue

            if product_tmpl.detailed_type != "product":
                continue

            variant = product_tmpl.product_variant_id
            if not variant:
                continue

            company = product_tmpl.company_id or variant.company_id or self.env.company
            move_vals_list.append({
                "name": f"Opening Stock - {variant.display_name}",
                "product_id": variant.id,
                "product_uom_qty": opening_qty,
                "product_uom": variant.uom_id.id,
                "location_id": inventory_location.id,
                "location_dest_id": stock_location.id,
                "company_id": company.id,
                "is_inventory": True,
            })

        if not move_vals_list:
            return

        moves = self.env["stock.move"].sudo().create(move_vals_list)
        moves._action_confirm()
        for move in moves:
            move._set_quantity_done(move.product_uom_qty)
        moves._action_done()

    def action_add_products_stock(self):
        updated_count = 0

        for product_tmpl in self:
            if product_tmpl.opening_stock_ref <= 0:
                continue

            if product_tmpl.detailed_type != "product":
                product_tmpl.write({"detailed_type": "product", "type": "product"})

            pending_qty = (product_tmpl.opening_stock_ref or 0.0) - (product_tmpl.opening_stock_added_qty or 0.0)
            if float_compare(pending_qty, 0.0, precision_rounding=product_tmpl.uom_id.rounding) <= 0:
                continue

            variant = product_tmpl.product_variant_id
            if not variant:
                continue

            new_qty = (variant.qty_available or 0.0) + pending_qty
            wizard = self.env["stock.change.product.qty"].create({
                "product_id": variant.id,
                "product_tmpl_id": product_tmpl.id,
                "new_quantity": new_qty,
            })
            wizard.change_product_qty()
            product_tmpl.opening_stock_added_qty = (product_tmpl.opening_stock_added_qty or 0.0) + pending_qty
            updated_count += 1

        message = _("Opening stock added for %s product(s).", updated_count)
        if not updated_count:
            message = _("No pending opening stock found.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Add Products"),
                "message": message,
                "type": "success" if updated_count else "warning",
                "sticky": False,
            },
        }
