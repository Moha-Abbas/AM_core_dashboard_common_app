"""
    User Dashboard constants
"""
from enum import Enum

from core_main_app.utils.labels import get_form_label, get_data_label

# Templates
DASHBOARD_HOME_TEMPLATE = "core_dashboard_common_app/home.html"
DASHBOARD_PROFILE_TEMPLATE = "core_dashboard_common_app/my_profile.html"
DASHBOARD_PROFILE_EDIT_TEMPLATE = (
    "core_dashboard_common_app/my_profile_edit.html"
)
DASHBOARD_PROFILE_CHANGE_PASSWORD_TEMPLATE = (
    "core_dashboard_common_app/my_profile_change_password.html"
)
RECORDS_DASHBOARD_TEMPLATE = "core_dashboard_common_app/my_records_dashboard.html"
DASHBOARD_TEMPLATE = "core_dashboard_common_app/my_dashboard.html"
ADMIN_DASHBOARD_TEMPLATE = "core_dashboard_common_app/admin/dashboard.html"

# Tables
DASHBOARD_RECORDS_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_records_table.html"
)
DASHBOARD_RECORDS_TEMPLATE_TABLE_DATATABLE = "core_dashboard_common_app/list/my_dashboard_my_records_table_datatable.html"
DASHBOARD_RECORDS_TEMPLATE_TABLE_PAGINATION = "core_dashboard_common_app/list/my_dashboard_my_records_table_pagination.html"
DASHBOARD_FORMS_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_forms_table.html"
)
DASHBOARD_TEMPLATES_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_templates_table.html"
)
DASHBOARD_TYPES_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_types_table.html"
)
DASHBOARD_FILES_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_files_table.html"
)
DASHBOARD_QUERIES_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_queries_table.html"
)
DASHBOARD_QUERIES_TEMPLATE_TABLE_PAGINATION = "core_dashboard_common_app/list/my_dashboard_my_queries_table_pagination.html"
DASHBOARD_WORKSPACES_TEMPLATE_TABLE = (
    "core_dashboard_common_app/list/my_dashboard_my_workspaces_table.html"
)

# Assets
MODALS_COMMON_DELETE = (
    "core_dashboard_common_app/list/modals/delete_document.html"
)
MODALS_COMMON_CHANGE_OWNER = (
    "core_dashboard_common_app/list/modals/change_owner.html"
)
MODALS_COMMON_DOWNLOAD_EXCEL_CONFIRM = (
    "core_dashboard_common_app/list/modals/download_excel_confirm.html"
)

# TODO: replace with the constants in core main app once they are done
CSS_COMMON = [
    "core_main_app/common/css/XMLTree.css",
    "core_main_app/common/css/table.css",
    "core_dashboard_common_app/common/css/list.css",
]
CSS_PROFILE = [
    "core_dashboard_common_app/common/css/profile.css",
]
JS_COMMON = [
    {"path": "core_dashboard_common_app/user/js/init.js", "is_raw": False},
]

JS_INIT_USER = "core_dashboard_common_app/user/js/init_user.js"
JS_USER_SELECTED_ELEMENT = (
    "core_dashboard_common_app/user/js/get_selected_document.js"
)
JS_COMMON_FUNCTION_DELETE = (
    "core_dashboard_common_app/user/js/list/modals/delete_document.js"
)
JS_COMMON_FUNCTION_CHANGE_OWNER = (
    "core_dashboard_common_app/user/js/list/modals/change_owner.js"
)
JS_EDIT_RECORD = "core_dashboard_common_app/user/js/list/edit_record.js"
USER_VIEW_RECORD_RAW = (
    "core_dashboard_common_app/user/js/list/view_record.raw.js"
)
JS_VIEW_RECORD = "core_dashboard_common_app/common/js/list/view_record.js"
JS_OPEN_DOCUMENT = "core_dashboard_common_app/common/js/list/open_document.js"

# Admin
JS_ADMIN_COUNT_CHECK = "core_dashboard_common_app/admin/js/count_checked.js"
JS_ADMIN_RESET_CHECKBOX = (
    "core_dashboard_common_app/admin/js/reset_checkbox.js"
)
JS_ADMIN_SELECT_ALL = "core_dashboard_common_app/admin/js/select_all.js"
JS_ADMIN_SELETED_ELEMENT = (
    "core_dashboard_common_app/admin/js/get_selected_document_admin.js"
)
JS_ADMIN_INIT_MENU = "core_dashboard_common_app/admin/js/init_admin_menu.js"
JS_ADMIN_ACTION_DASHBOARD = (
    "core_dashboard_common_app/admin/js/action_dashboard.js"
)
ADMIN_VIEW_RECORD_RAW = (
    "core_dashboard_common_app/admin/js/list/view_record.raw.js"
)

FUNCTIONAL_OBJECT_ENUM = Enum(
    "FUNCTIONAL_OBJECT_ENUM",
    {
        "RECORD": get_data_label(),
        "FORM": get_form_label(),
        "TEMPLATE": "template",
        "TYPE": "type",
        "FILE": "file",
        "QUERY": "query",
        "WORKSPACE": "workspace",
    },
)
