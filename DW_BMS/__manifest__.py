{
    "name": "DW BMS",
    "version": "1.0",
    "category": "Operations",
    "summary": "DW - Business Management System",
    "author": "Dreamwarez",
    "depends": [
        "base",
        "sale",
        "purchase",
        "account",
        "product",
        "stock",
        "mrp"
    ],
    "data": [
        "security/security.xml",
        "security/record_rules.xml",
        "security/ir.model.access.csv",
        "reports/sale_quotation_custom_report.xml",
        "reports/invoice_custom_report.xml",
        "views/res_partner_view.xml",
        "views/product_alias_view.xml",
        "views/account_move_view.xml",
        "views/sale_order_view.xml",
        'views/product_alert_views.xml',
        'views/product_extensions_view.xml',

        "wizard/bms_report_wizard_view.xml",
        "reports/bms_report_templates.xml",
    ],
    "installable": True,
    "application": True,
}
