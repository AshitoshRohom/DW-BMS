from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    supplier_type = fields.Selection(
        [
            ('individual', 'Individual'),
            ('business', 'Business'),
        ],
        string="Supplier Type",
        default='individual'
    )

    # NEW FIELD ADDED (SAFE)
    customer_type = fields.Selection(
        [
            ('wholesaler', 'Wholesaler'),
            ('retailer', 'Retailer'),
            ('end_user', 'End User'),
        ],
        string="Customer Type"
    )

    # ------------------------------------------------
    # STRICT UNIQUE VALIDATION
    # Phone & Mobile across system + same record check
    # ------------------------------------------------
    @api.constrains('phone', 'mobile')
    def _check_unique_phone_mobile(self):
        for partner in self:

            if partner.phone and partner.mobile and partner.phone == partner.mobile:
                raise ValidationError(
                    "Mobile 1 and Mobile 2 cannot be the same number."
                )

            if partner.phone:
                duplicate_phone = self.search([
                    ('id', '!=', partner.id),
                    '|',
                    ('phone', '=', partner.phone),
                    ('mobile', '=', partner.phone),
                    ('company_id', '=', partner.company_id.id),
                ], limit=1)

                if duplicate_phone:
                    raise ValidationError(
                        "Mobile 1 number is already used by another contact."
                    )

            if partner.mobile:
                duplicate_mobile = self.search([
                    ('id', '!=', partner.id),
                    '|',
                    ('phone', '=', partner.mobile),
                    ('mobile', '=', partner.mobile),
                    ('company_id', '=', partner.company_id.id),
                ], limit=1)

                if duplicate_mobile:
                    raise ValidationError(
                        "Mobile 2 number is already used by another contact."
                    )

    # -----------------------------------
    # GST REQUIRED FOR BUSINESS SUPPLIER
    # -----------------------------------
    @api.constrains('supplier_type', 'vat', 'supplier_rank')
    def _check_gst_for_business_supplier(self):
        for partner in self:
            if partner.supplier_rank > 0 and partner.supplier_type == 'business':
                if not partner.vat:
                    raise ValidationError(
                        "GST Number (Tax ID) is mandatory for Business Suppliers."
                    )




class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    hsn_code = fields.Char(
        string="HSN",
        related="product_id.l10n_in_hsn_code",
        store=True
    )



class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    hsn_code = fields.Char(
        string="HSN",
        related="product_id.l10n_in_hsn_code",
        store=True
    )
