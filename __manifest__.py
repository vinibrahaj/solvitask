{
    'name': 'SolviTask',
    'version': '17.0.1.0.0',
    'summary': 'Plumbing & heating service management',
    'description': 'Customers, plumbers, jobs, services, tools and materials.',
    'category': 'Services',
    'author': 'Author',
    'website': 'Website',
    'depends': ['base', 'web'],
    'data': [
        'security/solvitask_security.xml',
        'security/ir.model.access.csv',
        'data/job_stage_data.xml',
        'report/job_invoice_report.xml',
        'views/menus.xml',
        'views/customer_view.xml',
        'views/worker_view.xml',
        'views/service_view.xml',
        'views/tool_view.xml',
        'views/material_view.xml',
        'views/job_stage_view.xml',
        'views/job_view.xml',
<<<<<<< HEAD
        'views/requests_view.xml',
=======
        'views/job_request_view.xml',
>>>>>>> 363dfc8b76f846a74b25bc46b5cb73d0d99f3377
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
