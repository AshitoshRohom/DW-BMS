from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    bill_to_same_as_customer = fields.Boolean(
        string="Bill To Same as Customer Address",
        default=True,
        copy=False,
    )
    ship_to_same_as_customer = fields.Boolean(
        string="Ship To Same as Customer Address",
        default=True,
        copy=False,
    )
    bill_to_address = fields.Text(
        string="Bill To Address",
        copy=False,
    )
    bill_to_city = fields.Char(string="Bill To City", copy=False)
    bill_to_state_id = fields.Many2one("res.country.state", string="Bill To State", copy=False)
    bill_to_zip = fields.Char(string="Bill To PIN Code", copy=False)
    ship_to_address = fields.Text(
        string="Ship To Address",
        copy=False,
    )
    ship_to_city = fields.Char(string="Ship To City", copy=False)
    ship_to_state_id = fields.Many2one("res.country.state", string="Ship To State", copy=False)
    ship_to_zip = fields.Char(string="Ship To PIN Code", copy=False)

    # Backward compatibility for previously loaded views.
    bill_to_partner_id = fields.Many2one("res.partner", string="Bill To Partner", copy=False)
    ship_to_partner_id = fields.Many2one("res.partner", string="Ship To Partner", copy=False)
    bill_to_address_text = fields.Text(string="Bill To Address Text", compute="_compute_legacy_address_text")
    ship_to_address_text = fields.Text(string="Ship To Address Text", compute="_compute_legacy_address_text")

    @api.depends("bill_to_address", "bill_to_city", "bill_to_state_id", "bill_to_zip", "ship_to_address", "ship_to_city", "ship_to_state_id", "ship_to_zip")
    def _compute_legacy_address_text(self):
        for move in self:
            bill_state = move.bill_to_state_id.name if move.bill_to_state_id else False
            ship_state = move.ship_to_state_id.name if move.ship_to_state_id else False
            move.bill_to_address_text = "\n".join(
                [p for p in [move.bill_to_address, move.bill_to_city, bill_state, move.bill_to_zip] if p]
            ) or False
            move.ship_to_address_text = "\n".join(
                [p for p in [move.ship_to_address, move.ship_to_city, ship_state, move.ship_to_zip] if p]
            ) or False

    def _partner_address_vals(self, partner, prefix):
        if not partner:
            return {
                f"{prefix}_address": False,
                f"{prefix}_city": False,
                f"{prefix}_state_id": False,
                f"{prefix}_zip": False,
            }
        address_lines = [line for line in (partner.street, partner.street2) if line]
        return {
            f"{prefix}_address": "\n".join(address_lines) if address_lines else False,
            f"{prefix}_city": partner.city or False,
            f"{prefix}_state_id": partner.state_id.id or False,
            f"{prefix}_zip": partner.zip or False,
        }

    @api.onchange('partner_id')
    def _onchange_partner_set_fiscal_position(self):
        if self.partner_id:
            if self.bill_to_same_as_customer:
                self.update(self._partner_address_vals(self.partner_id, "bill_to"))
            if self.ship_to_same_as_customer:
                self.update(self._partner_address_vals(self.partner_shipping_id or self.partner_id, "ship_to"))

        if not self.partner_id or not self.company_id:
            return

        company_state = self.company_id.state_id
        partner_state = self.partner_id.state_id

        if not company_state or not partner_state:
            return

        FiscalPosition = self.env['account.fiscal.position']

        # Intra-state (same state)
        if company_state.id == partner_state.id:
            fiscal_position = FiscalPosition.search([
                ('name', '=', 'GST Intra State'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        else:
            # Inter-state (different state)
            fiscal_position = FiscalPosition.search([
                ('name', '=', 'GST Inter State'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

        if fiscal_position:
            self.fiscal_position_id = fiscal_position

    @api.onchange("bill_to_same_as_customer")
    def _onchange_bill_to_same_as_customer(self):
        if self.bill_to_same_as_customer:
            self.update(self._partner_address_vals(self.partner_id, "bill_to"))
        else:
            self.update(self._partner_address_vals(False, "bill_to"))

    @api.onchange("ship_to_same_as_customer")
    def _onchange_ship_to_same_as_customer(self):
        if self.ship_to_same_as_customer:
            self.update(self._partner_address_vals(self.partner_shipping_id or self.partner_id, "ship_to"))
        else:
            self.update(self._partner_address_vals(False, "ship_to"))

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves.filtered(lambda m: m.move_type in ("out_invoice", "out_refund")):
            updates = {}
            if move.bill_to_same_as_customer and move.partner_id:
                updates.update(move._partner_address_vals(move.partner_id, "bill_to"))
            if move.ship_to_same_as_customer and move.partner_id:
                updates.update(move._partner_address_vals(move.partner_shipping_id or move.partner_id, "ship_to"))
            if updates:
                move.write(updates)
        return moves

    def write(self, vals):
        result = super().write(vals)
        if "partner_id" in vals:
            for move in self.filtered(lambda m: m.move_type in ("out_invoice", "out_refund")):
                updates = {}
                if move.bill_to_same_as_customer and move.partner_id:
                    updates.update(move._partner_address_vals(move.partner_id, "bill_to"))
                if move.ship_to_same_as_customer and move.partner_id:
                    updates.update(move._partner_address_vals(move.partner_shipping_id or move.partner_id, "ship_to"))
                if updates:
                    super(AccountMove, move).write(updates)
        return result


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    hsn_code = fields.Char(
        string="HSN",
        related="product_id.l10n_in_hsn_code",
        store=True,
    )
