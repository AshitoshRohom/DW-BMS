from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ProductNameAlias(models.Model):
    _name = "dw.product.name.alias"
    _description = "Product Alternate Name"
    _order = "name"

    name = fields.Char(string="Alternate Name", required=True, index=True)
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name"):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("name"):
            vals["name"] = vals["name"].strip()
        return super().write(vals)

    @api.constrains("name")
    def _check_unique_name_case_insensitive(self):
        for alias in self:
            if not alias.name:
                continue
            normalized_name = alias.name.strip()
            duplicate = self.search(
                [("id", "!=", alias.id), ("name", "=ilike", normalized_name)],
                limit=1,
            )
            if duplicate:
                raise ValidationError("Alternate name must be unique across products.")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    alias_ids = fields.One2many(
        "dw.product.name.alias",
        "product_tmpl_id",
        string="Alternate Names",
        copy=True,
    )

    def _check_sales_price_edit_access(self, vals):
        if self.env.su or self.env.user.has_group("DW_BMS.group_bms_admin"):
            return
        if "list_price" in vals:
            raise ValidationError("Only BMS Admin can change Product Sales Price.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_sales_price_edit_access(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._check_sales_price_edit_access(vals)
        return super().write(vals)

    @api.model
    def _name_search(self, name="", domain=None, operator="ilike", limit=None, order=None):
        domain = domain or []
        ids = super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
        if not name:
            return ids

        alias_templates = self.env["dw.product.name.alias"].search([("name", operator, name)]).mapped("product_tmpl_id")
        if not alias_templates:
            return ids

        existing_ids = list(ids)
        remaining = (limit - len(existing_ids)) if limit else None
        if limit and remaining <= 0:
            return existing_ids

        extra_domain = expression.AND([
            domain,
            [("id", "in", alias_templates.ids), ("id", "not in", existing_ids)],
        ])
        extra_ids = self._search(extra_domain, limit=remaining, order=order)
        return existing_ids + extra_ids


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _check_sales_price_edit_access(self, vals):
        if self.env.su or self.env.user.has_group("DW_BMS.group_bms_admin"):
            return
        if "list_price" in vals:
            raise ValidationError("Only BMS Admin can change Product Sales Price.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_sales_price_edit_access(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._check_sales_price_edit_access(vals)
        return super().write(vals)

    @api.model
    def _name_search(self, name="", domain=None, operator="ilike", limit=None, order=None):
        domain = domain or []
        ids = super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
        if not name:
            return ids

        alias_templates = self.env["dw.product.name.alias"].search([("name", operator, name)]).mapped("product_tmpl_id")
        if not alias_templates:
            return ids

        existing_ids = list(ids)
        remaining = (limit - len(existing_ids)) if limit else None
        if limit and remaining <= 0:
            return existing_ids

        extra_domain = expression.AND([
            domain,
            [("product_tmpl_id", "in", alias_templates.ids), ("id", "not in", existing_ids)],
        ])
        extra_ids = self._search(extra_domain, limit=remaining, order=order)
        return existing_ids + extra_ids
