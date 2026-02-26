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
        
        products = self.search([('type', '=', 'product')])
        low_stock_ids = []
        for product in products:
            if product.qty_available < (product.min_alert_qty or 0.0):
                low_stock_ids.append(product.id)
                
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('id', 'in', low_stock_ids)]
        else:
            return [('id', 'not in', low_stock_ids)]

    # ------------------------------------------------------------------
    # Purchase Status Fields
    # ------------------------------------------------------------------

    purchase_status = fields.Selection(
        selection=[
            ('no_order', 'No Order'),
            ('ordered', 'Ordered'),
            ('stock_received', 'Stock Received'),
        ],
        string='Purchase Status',
        compute='_compute_purchase_status',
        help="Reflects the latest confirmed purchase order status for this product.",
    )

    purchase_vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        compute='_compute_purchase_status',
        help="Vendor from the latest confirmed purchase order (shown only when status is 'Ordered').",
    )

    @api.depends(
        'product_tmpl_id',
    )
    def _compute_purchase_status(self):
        """
        Batch-friendly compute for purchase_status and purchase_vendor_id.

        Priority:
          1. Confirmed PO (state='purchase') with at least one incoming
             picking NOT yet done → status='Ordered', vendor=PO partner
          2. Confirmed PO (state='purchase') where ALL incoming pickings
             ARE done → status='Stock Received', vendor=False
          3. No confirmed PO at all → status='No Order', vendor=False
        """
        product_ids = self.ids
        if not product_ids:
            return

        # ── Step 1: fetch all confirmed PO lines for these products ──────
        PurchaseOrderLine = self.env['purchase.order.line'].sudo()
        pol_data = PurchaseOrderLine.search_read(
            domain=[
                ('product_id', 'in', product_ids),
                ('order_id.state', 'in', ['purchase', 'done']),
            ],
            fields=['product_id', 'order_id'],
        )

        # Map product_id → list of order_ids
        product_to_orders = {}
        for pol in pol_data:
            pid = pol['product_id'][0]
            oid = pol['order_id'][0]
            product_to_orders.setdefault(pid, set()).add(oid)

        # ── Step 2: for each relevant order fetch picking state ──────────
        all_order_ids = {oid for oids in product_to_orders.values() for oid in oids}

        # Map order_id → list of (picking_state)
        order_picking_states = {}
        if all_order_ids:
            StockPicking = self.env['stock.picking'].sudo()
            picking_data = StockPicking.search_read(
                domain=[
                    ('purchase_id', 'in', list(all_order_ids)),
                    ('picking_type_code', '=', 'incoming'),
                ],
                fields=['purchase_id', 'state'],
            )
            for pk in picking_data:
                oid = pk['purchase_id'][0]
                order_picking_states.setdefault(oid, []).append(pk['state'])

        # ── Step 3: fetch partner per order ─────────────────────────────
        order_partner = {}
        if all_order_ids:
            PurchaseOrder = self.env['purchase.order'].sudo()
            po_data = PurchaseOrder.search_read(
                domain=[('id', 'in', list(all_order_ids))],
                fields=['partner_id'],
            )
            for po in po_data:
                order_partner[po['id']] = po['partner_id'][0] if po['partner_id'] else False

        # ── Step 4: assign per product ───────────────────────────────────
        for product in self:
            order_ids = product_to_orders.get(product.id)
            if not order_ids:
                product.purchase_status = 'no_order'
                product.purchase_vendor_id = False
                continue

            # Check if any confirmed order has a pending (not-done) receipt
            ordered_vendor = False
            all_received = True

            for oid in order_ids:
                pick_states = order_picking_states.get(oid, [])
                if not pick_states:
                    # PO confirmed but no picking created yet → still pending
                    all_received = False
                    ordered_vendor = order_partner.get(oid, False)
                    break
                if any(s != 'done' for s in pick_states):
                    all_received = False
                    ordered_vendor = order_partner.get(oid, False)
                    break

            if not all_received and ordered_vendor:
                product.purchase_status = 'ordered'
                product.purchase_vendor_id = ordered_vendor
            elif all_received:
                product.purchase_status = 'stock_received'
                product.purchase_vendor_id = False
            else:
                product.purchase_status = 'no_order'
                product.purchase_vendor_id = False
