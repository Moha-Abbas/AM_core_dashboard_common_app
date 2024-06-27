""" Django settings for core_dashboard_common_app app.

Settings with the following syntax can be overwritten at the project level:
SETTING_NAME = getattr(settings, "SETTING_NAME", "Default Value")
"""

from django.conf import settings

if not settings.configured:
    settings.configure()

SERVER_URI = getattr(settings, "SERVER_URI", "http://localhost")

INSTALLED_APPS = getattr(settings, "INSTALLED_APPS", [])

# Number of documents to display per page for pagination
RESULTS_PER_PAGE = getattr(settings, "RESULTS_PER_PAGE", 50)

# Number of forms to display per page for pagination
FORM_PER_PAGE_PAGINATION = getattr(
    settings, "FORM_PER_PAGE_PAGINATION", RESULTS_PER_PAGE
)

# Number of records to display per page for pagination
RECORD_PER_PAGE_PAGINATION = getattr(
    settings, "RECORD_PER_PAGE_PAGINATION", RESULTS_PER_PAGE
)

# Number of files to display per page for pagination
FILE_PER_PAGE_PAGINATION = getattr(
    settings, "FILE_PER_PAGE_PAGINATION", RESULTS_PER_PAGE
)

# Number of queries to display per page for pagination
QUERY_PER_PAGE_PAGINATION = getattr(
    settings, "QUERY_PER_PAGE_PAGINATION", RESULTS_PER_PAGE
)

# Set Workspace public
CAN_SET_WORKSPACE_PUBLIC = getattr(settings, "CAN_SET_WORKSPACE_PUBLIC", True)
