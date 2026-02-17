from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

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
        help="Reference field for imported opening stock. Does not affect actual inventory levels.",
    )
