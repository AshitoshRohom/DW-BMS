{
    'name': 'DW Home Dashboard',
    'version': '17.0.1.0.0',
    'summary': 'Operational Home Dashboard with Alerts',
    'author': 'Dreamwarez',
    'depends': [
        'base',
        'sale',
        'purchase',
        'account',
        'stock',
        'mrp',
        'spreadsheet_dashboard',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        'views/dashboard_view.xml',
    ],
    'installable': True,
    'application': True,
}
