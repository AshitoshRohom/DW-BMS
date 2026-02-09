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
        "product"
    ],
    "data": [
        "security/security.xml",
        "security/record_rules.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": True,
}
