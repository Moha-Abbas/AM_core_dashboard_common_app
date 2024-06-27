""" Common views
"""
import copy
import math

from django.conf import settings as conf_settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http.response import HttpResponseRedirect
from django.urls import reverse

import core_main_app.components.data.api as workspace_data_api
from core_explore_common_app.components.abstract_persistent_query import (
    api as abstract_persistent_query_api,
)
from core_explore_common_app.components.abstract_persistent_query.models import (
    AbstractPersistentQuery,
)
from core_explore_common_app.views.user.views import ResultQueryRedirectView
from core_main_app.access_control.exceptions import AccessControlError
from core_main_app.commons.exceptions import DoesNotExist
from core_main_app.components.blob import api as blob_api, utils as blob_utils
from core_main_app.components.data import api as data_api
from core_main_app.components.template import api as template_api
from core_main_app.components.template_version_manager import (
    api as template_version_manager_api,
)
from core_main_app.components.user import api as user_api
from core_main_app.components.user.api import get_id_username_dict
from core_main_app.components.workspace import api as workspace_api
from core_main_app.components.workspace.api import (
    check_if_workspace_can_be_changed,
)
from core_main_app.settings import INSTALLED_APPS
from core_main_app.utils.labels import get_data_label
from core_main_app.utils.pagination.django_paginator.results_paginator import (
    ResultsPaginator,
)
from core_main_app.utils.rendering import render
from core_main_app.views.admin.forms import EditProfileForm
from core_main_app.views.common.ajax import EditTemplateVersionManagerView
from core_main_app.views.common.views import CommonView
from core_main_app.views.user.forms import WorkspaceForm, BlobFileForm

if "core_curate_app" in INSTALLED_APPS:
    import core_curate_app.components.curate_data_structure.api as curate_data_structure_api
if "core_composer_app" in INSTALLED_APPS:
    from core_composer_app.components.type_version_manager import (
        api as type_version_manager_api,
    )
    from core_composer_app.components.type import api as type_api
    from core_composer_app.views.user.ajax import EditTypeVersionManagerView
from core_dashboard_common_app import constants as dashboard_constants
from core_dashboard_common_app import settings
from core_dashboard_common_app.views.common.forms import ActionForm, UserForm
from core_dashboard_common_app.views.common.record_filters import (
    filter_records,
)


@login_required
def home(request):
    """Home page.

    Args:
        request:

    Returns:
    """
    return render(
        request,
        dashboard_constants.DASHBOARD_HOME_TEMPLATE,
        context={"page_title": "Dashboard"},
    )


@login_required
def my_profile(request):
    """User's profile information page.

    Args:
        request:

    Returns:
    """
    return render(
        request,
        dashboard_constants.DASHBOARD_PROFILE_TEMPLATE,
        context={
            "page_title": "My Profile",
            "ENABLE_SAML2_SSO_AUTH": conf_settings.ENABLE_SAML2_SSO_AUTH,
        },
        assets={"css": dashboard_constants.CSS_PROFILE},
    )


@login_required
def my_profile_edit(request):
    """Edit the profile.

    Args:
        request:

    Returns:
    """
    if request.method == "POST":
        form = _get_edit_profile_form(
            request=request,
            template=dashboard_constants.DASHBOARD_PROFILE_EDIT_TEMPLATE,
        )
        if form.is_valid():
            user = request.user
            user.first_name = request.POST["firstname"]
            user.last_name = request.POST["lastname"]
            user.email = request.POST["email"]
            try:
                user_api.upsert(user)
            except IntegrityError as exception:
                if "unique constraint" in str(exception):
                    message = "A user with the same username already exists."
                    return render(
                        request,
                        dashboard_constants.DASHBOARD_PROFILE_EDIT_TEMPLATE,
                        context={
                            "form": form,
                            "action_result": message,
                            "page_title": "Error",
                        },
                    )
                else:
                    _error_while_saving(request, form)
            except Exception:
                _error_while_saving(request, form)

            messages.add_message(
                request,
                messages.SUCCESS,
                "Profile information edited.",
            )
            return HttpResponseRedirect(reverse("core_dashboard_profile"))
        return render(
            request,
            dashboard_constants.DASHBOARD_PROFILE_EDIT_TEMPLATE,
            context={"form": form, "page_title": "Edit Profile"},
            assets={"css": dashboard_constants.CSS_PROFILE},
        )
    user = request.user
    data = {
        "firstname": user.first_name,
        "lastname": user.last_name,
        "username": user.username,
        "email": user.email,
    }
    form = _get_edit_profile_form(
        request, dashboard_constants.DASHBOARD_PROFILE_TEMPLATE, initial=data
    )

    return render(
        request,
        dashboard_constants.DASHBOARD_PROFILE_EDIT_TEMPLATE,
        context={"form": form, "page_title": "Edit Profile"},
        assets={"css": dashboard_constants.CSS_PROFILE},
    )


@login_required
def my_profile_change_password(request):
    """Change the connected user's password.

    Args:
        request:

    Returns:
    """
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # keep the user logged in after their password hash changes
            update_session_auth_hash(request, user)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Password changed successfully.",
            )
            return HttpResponseRedirect(reverse("core_dashboard_profile"))
    else:
        form = PasswordChangeForm(user=request.user)

    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")

    return render(
        request,
        dashboard_constants.DASHBOARD_PROFILE_CHANGE_PASSWORD_TEMPLATE,
        context={"form": form, "page_title": "Change Password"},
        assets={"css": dashboard_constants.CSS_PROFILE},
    )


def _get_edit_profile_form(request, template, initial=None):
    """Build the edit-profile form.

    On GET, `initial` holds the user's current values and the form is left
    unbound so it displays them without triggering "required" validation
    errors. On POST (`initial=None`), the form is bound to `request.POST`
    to validate the submission.

    Args:
        request
        template
        initial

    Returns:
    """
    try:
        form = (
            EditProfileForm(initial=initial)
            if initial is not None
            else EditProfileForm(request.POST)
        )
        for field in form.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        return form
    except Exception:
        message = "A problem with the form has occurred."
        return render(
            request,
            template,
            context={"action_result": message, "page_title": "Error"},
        )


def _error_while_saving(request, form):
    """Raise exception if uncatched problems occurred while saving.

    Args:
        request
        form

    Returns:
    """
    message = "A problem has occurred while saving the user."
    return render(
        request,
        dashboard_constants.DASHBOARD_PROFILE_EDIT_TEMPLATE,
        context={
            "form": form,
            "action_result": message,
            "page_title": "Error",
        },
    )


class DashboardRecords(CommonView):
    """List the records."""

    template = dashboard_constants.RECORDS_DASHBOARD_TEMPLATE
    data_template = (
        dashboard_constants.DASHBOARD_RECORDS_TEMPLATE_TABLE_PAGINATION
    )
    document = dashboard_constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value
    allow_change_workspace_if_public = True

    def get(self, request, *args, **kwargs):
        """get

        Args:
            request:
            args:
            kwargs:

        Returns:

        """

        # Get records
        if self.administration:
            try:
                base_data = data_api.get_all(request.user)

            except AccessControlError:
                base_data = data_api.get_none()

        else:
            base_data = data_api.get_all_by_user(request.user)

        # Filters (search / workspace / test)
        search = request.GET.get("search", "").strip()
        workspace_filter = request.GET.get("workspace", "").strip()
        template_filter = request.GET.get("template", "").strip()

        loaded_data = filter_records(base_data, request.GET)

        # Paginator
        page = request.GET.get("page", 1)
        results_paginator = ResultsPaginator.get_results(
            loaded_data, page, settings.RECORD_PER_PAGE_PAGINATION
        )

        # Data context
        try:
            results_paginator.object_list = self._format_data_context(
                results_paginator.object_list, request.user
            )
        except Exception:
            results_paginator.object_list = []

        # Filter dropdown options + the label to show in the closed dropdown
        workspace_options = workspace_api.get_by_id_list(
            base_data.exclude(workspace__isnull=True)
            .order_by()
            .values_list("workspace_id", flat=True)
            .distinct()
        )
        template_options = template_api.get_all_accessible_by_id_list(
            list(
                base_data.order_by()
                .values_list("template_id", flat=True)
                .distinct()
            ),
            request=request,
        )

        if workspace_filter == "none":
            workspace_filter_label = "No workspace"
        elif workspace_filter:
            workspace_filter_label = next(
                (
                    workspace.title
                    for workspace in workspace_options
                    if str(workspace.id) == workspace_filter
                ),
                "All workspaces",
            )
        else:
            workspace_filter_label = "All workspaces"

        if template_filter:
            template_filter_label = next(
                (
                    template.display_name
                    for template in template_options
                    if str(template.id) == template_filter
                ),
                "All tests",
            )
        else:
            template_filter_label = "All tests"

        # Add user_form for change owner
        user_form = UserForm(request.user)
        context = {
            "number_total": loaded_data.count(),
            "user_data": results_paginator,
            "user_form": user_form,
            "document": self.document,
            "template": self.data_template,
            "action_form": ActionForm(
                [
                    ("1", "Delete selected records"),
                    ("2", "Change owner of selected records"),
                    ("3", "Move selected records to a workspace"),
                ]
            ),
            "menu": self.administration,
            "administration": self.administration,
            "share_pid_button": "core_linked_records_app"
            in settings.INSTALLED_APPS,
            "search_value": search,
            "workspace_filter": workspace_filter,
            "template_filter": template_filter,
            "workspace_filter_label": workspace_filter_label,
            "template_filter_label": template_filter_label,
            "workspace_options": workspace_options,
            "template_options": template_options,
        }

        if self.administration:
            context.update(
                {
                    "username_list": get_id_username_dict(
                        user_api.get_all_users()
                    ),
                }
            )

        modals = [
            "core_main_app/user/workspaces/list/modals/assign_workspace.html",
            dashboard_constants.MODALS_COMMON_DELETE,
            dashboard_constants.MODALS_COMMON_CHANGE_OWNER,
            dashboard_constants.MODALS_COMMON_DOWNLOAD_EXCEL_CONFIRM,
        ]

        assets = self._get_assets()

        if context["share_pid_button"]:
            modals.append(
                "core_linked_records_app/user/sharing/data_detail/modal.html"
            )
            assets["css"].append("core_main_app/common/css/share_link.css"),

            assets["js"] += [
                {
                    "path": "core_main_app/user/js/sharing_modal.js",
                    "is_raw": False,
                },
                {
                    "path": "core_linked_records_app/user/js/sharing/common_list.js",
                    "is_raw": False,
                },
                {
                    "path": "core_linked_records_app/user/js/sharing/data_list.js",
                    "is_raw": False,
                },
            ]

        # Set page title
        context.update({"page_title": "My Data"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )

    def _format_data_context(self, data_list, user):
        data_context_list = []

        for data in data_list:
            forms_count = (
                len(
                    curate_data_structure_api.get_all_curate_data_structures_by_data(
                        data, user
                    )
                )
                if self.administration
                else 0
            )
            data_context_list.append(
                {
                    "data": data,
                    "can_read": True,
                    "can_write": True,
                    "is_owner": True,
                    "forms_count": forms_count,
                    "form_id": self._get_form(data, user),
                    "can_change_workspace": check_if_workspace_can_be_changed(
                        data
                    ),
                }
            )
        return data_context_list

    def _get_form(self, data, user):
        try:
            return curate_data_structure_api.get_by_data_id_and_user(
                data.id, user
            ).id
        except DoesNotExist:
            return None

    def _get_assets(self):
        assets = {
            "css": copy.deepcopy(dashboard_constants.CSS_COMMON),
            "js": [
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/assign_workspace.js",
                    "is_raw": False,
                },
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/assign_data_workspace.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
                {"path": dashboard_constants.JS_EDIT_RECORD, "is_raw": False},
                {"path": dashboard_constants.JS_VIEW_RECORD, "is_raw": False},
                {
                    "path": dashboard_constants.JS_OPEN_DOCUMENT,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/open_record.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/delete_data_draft.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/open_form.raw.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_CHANGE_OWNER,
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": "core_main_app/common/js/tooltip.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/download_user_data.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/download_user_data.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_main_app/common/js/wait/waiting.js",
                    "is_raw": False,
                },
            ],
        }

        assets["css"].append("core_main_app/common/css/wait/waiting.css")

        # Bulk-select (checkboxes, select all, bulk action dropdown): shared
        # between admin and regular views so "Modify Records" works for both.
        assets["js"].append(
            {
                "path": "core_dashboard_common_app/admin/js/action_dashboard.js",
                "is_raw": True,
            }
        )
        assets["js"].append(
            {
                "path": dashboard_constants.JS_ADMIN_COUNT_CHECK,
                "is_raw": True,
            }
        )
        assets["js"].append(
            {
                "path": dashboard_constants.JS_ADMIN_RESET_CHECKBOX,
                "is_raw": True,
            }
        )
        assets["js"].append(
            {
                "path": dashboard_constants.JS_ADMIN_SELECT_ALL,
                "is_raw": True,
            }
        )
        assets["js"].append(
            {
                "path": dashboard_constants.JS_ADMIN_SELETED_ELEMENT,
                "is_raw": False,
            }
        )
        assets["js"].append(
            {
                "path": dashboard_constants.JS_ADMIN_INIT_MENU,
                "is_raw": False,
            }
        )
        assets["js"].append(
            {
                "path": "core_dashboard_common_app/user/js/list/record_ids.raw.js",
                "is_raw": True,
            }
        )
        assets["js"].append(
            {
                "path": "core_dashboard_common_app/user/js/list/records_bulk_select.js",
                "is_raw": False,
            }
        )
        assets["js"].append(
            {
                "path": "core_dashboard_common_app/user/js/list/combo_select.js",
                "is_raw": False,
            }
        )

        # Admin
        if self.administration:
            assets["js"].append(
                {
                    "path": dashboard_constants.ADMIN_VIEW_RECORD_RAW,
                    "is_raw": True,
                }
            )
        else:
            assets["js"].append(
                {
                    "path": dashboard_constants.USER_VIEW_RECORD_RAW,
                    "is_raw": True,
                }
            )

        return assets


class DashboardFiles(CommonView):
    """List the files."""

    template = dashboard_constants.DASHBOARD_TEMPLATE
    allow_change_workspace_if_public = True

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """
        reverse_url = "core-admin:core_main_app_blob_detail"
        if self.administration:
            try:
                files = blob_api.get_all(request.user)

            except AccessControlError:
                files = blob_api.get_none()
        else:
            reverse_url = "core_main_app_blob_detail"
            files = blob_api.get_all_by_user(request.user)

        # Paginator
        page = request.GET.get("page", 1)
        results_paginator = ResultsPaginator.get_results(
            files, page, settings.FILE_PER_PAGE_PAGINATION
        )
        detailed_file = []
        for file in results_paginator:
            try:
                username = user_api.get_user_by_id(file.user_id).username
            except ObjectDoesNotExist:
                username = "None"
            detailed_file.append(
                {
                    "user": username,
                    "date": file.creation_date,
                    "file": file,
                    "url": f"{reverse(reverse_url)}?id={file.id}",
                    "download_url": blob_utils.get_blob_download_uri(
                        file, request
                    ),
                    "can_change_workspace": check_if_workspace_can_be_changed(
                        file
                    ),
                    "is_owner": True,
                }
            )

        # Add user_form for change owner
        user_form = UserForm(request.user)
        file_upload_form = BlobFileForm()
        context = {
            "administration": self.administration,
            "number_total": files.count(),
            "user_data": detailed_file,
            "user_form": user_form,
            "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.FILE.value,
            "template": dashboard_constants.DASHBOARD_FILES_TEMPLATE_TABLE,
            "menu": self.administration,
            "file_upload_form": file_upload_form,
            "share_pid_button": "core_linked_records_app"
            in settings.INSTALLED_APPS,
            "pagination": _get_pagination_document(
                page,
                results_paginator,
                files.count(),
                settings.FILE_PER_PAGE_PAGINATION,
            ),
        }

        if self.administration:
            context.update(
                {
                    "action_form": ActionForm(
                        [
                            ("1", "Delete selected files"),
                            ("2", "Change owner of selected files"),
                        ]
                    )
                }
            )

        modals = [
            "core_main_app/user/workspaces/list/modals/assign_workspace.html",
            "core_main_app/user/blob/list/modals/file_upload.html",
            dashboard_constants.MODALS_COMMON_DELETE,
            dashboard_constants.MODALS_COMMON_CHANGE_OWNER,
        ]

        assets = {
            "css": dashboard_constants.CSS_COMMON,
            "js": [
                {
                    "path": "core_dashboard_common_app/user/js/list/modals/upload_file.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_USER_SELECTED_ELEMENT,
                    "is_raw": True,
                },
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/assign_workspace.js",
                    "is_raw": False,
                },
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/assign_blob_workspace.raw.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_CHANGE_OWNER,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                },
            ],
        }

        if "core_file_preview_app" in conf_settings.INSTALLED_APPS:
            assets["js"].extend(
                [
                    {
                        "path": "core_file_preview_app/user/js/file_preview.js",
                        "is_raw": False,
                    }
                ]
            )
            assets["css"].append(
                "core_file_preview_app/user/css/file_preview.css"
            )
            modals.append("core_file_preview_app/user/file_preview_modal.html")

        if context["share_pid_button"]:
            modals.append(
                "core_linked_records_app/user/sharing/data_detail/modal.html"
            )

            assets["css"].append("core_main_app/common/css/share_link.css"),
            assets["js"] += [
                {
                    "path": "core_main_app/user/js/sharing_modal.js",
                    "is_raw": False,
                },
                {
                    "path": "core_linked_records_app/user/js/sharing/common_list.js",
                    "is_raw": False,
                },
                {
                    "path": "core_linked_records_app/user/js/sharing/blob_list.js",
                    "is_raw": False,
                },
            ]

        # Admin
        if self.administration:
            assets["js"].append(
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_ACTION_DASHBOARD,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_COUNT_CHECK,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_RESET_CHECKBOX,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELECT_ALL,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELETED_ELEMENT,
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_INIT_MENU,
                    "is_raw": False,
                }
            )

        # Set page title
        context.update({"page_title": "Files"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )


class DashboardForms(CommonView):
    """List the forms."""

    template = dashboard_constants.DASHBOARD_TEMPLATE
    document = dashboard_constants.FUNCTIONAL_OBJECT_ENUM.FORM.value

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """

        # Get the forms
        if self.administration:
            try:
                forms = curate_data_structure_api.get_all_with_no_data(
                    request.user
                )
            except AccessControlError:
                forms = curate_data_structure_api.get_none()
        else:
            forms = curate_data_structure_api.get_all_by_user_id_with_no_data(
                request.user.id
            )

        # Paginator
        page = request.GET.get("page", 1)
        results_paginator = ResultsPaginator.get_results(
            forms, page, settings.FORM_PER_PAGE_PAGINATION
        )
        try:
            detailed_forms = self._get_detailed_forms(results_paginator)
        except Exception:
            detailed_forms = []

        context = {
            "administration": self.administration,
            "number_total": forms.count(),
            "user_data": detailed_forms,
            "user_form": UserForm(request.user),
            "document": self.document,
            "template": dashboard_constants.DASHBOARD_FORMS_TEMPLATE_TABLE,
            "menu": self.administration,
            "pagination": _get_pagination_document(
                page,
                results_paginator,
                forms.count(),
                settings.FORM_PER_PAGE_PAGINATION,
            ),
        }

        modals = [
            "core_main_app/user/workspaces/list/modals/assign_workspace.html",
            dashboard_constants.MODALS_COMMON_DELETE,
            dashboard_constants.MODALS_COMMON_CHANGE_OWNER,
        ]

        assets = {
            "css": dashboard_constants.CSS_COMMON,
            "js": [
                {
                    "path": dashboard_constants.JS_OPEN_DOCUMENT,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/open_form.raw.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_CHANGE_OWNER,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                },
            ],
        }

        if self.administration:
            # Get all username and corresponding ids
            user_names = dict(
                (str(x.id), x.username) for x in user_api.get_all_users()
            )
            context.update(
                {
                    "usernames": user_names,
                    "action_form": ActionForm(
                        [
                            ("1", "Delete selected forms"),
                            ("2", "Change owner of selected forms"),
                        ]
                    ),
                }
            )

            assets["js"].extend(
                [
                    {
                        "path": "core_dashboard_common_app/common/js/init_pagination.js",
                        "is_raw": False,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_ACTION_DASHBOARD,
                        "is_raw": True,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_COUNT_CHECK,
                        "is_raw": True,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_RESET_CHECKBOX,
                        "is_raw": True,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_SELECT_ALL,
                        "is_raw": True,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_SELETED_ELEMENT,
                        "is_raw": False,
                    },
                    {
                        "path": dashboard_constants.JS_ADMIN_INIT_MENU,
                        "is_raw": False,
                    },
                ]
            )
        else:
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_USER_SELECTED_ELEMENT,
                    "is_raw": True,
                }
            )

        # Set page title
        context.update({"page_title": "Dashboard"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )

    def _get_detailed_forms(self, forms):
        detailed_forms = []
        for form in forms:
            detailed_forms.append({"form": form})
        return list(reversed(detailed_forms))


class DashboardTemplates(CommonView):
    """List the templates."""

    template = dashboard_constants.DASHBOARD_TEMPLATE

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """
        try:
            # Get templates
            if self.administration:
                template_versions = template_version_manager_api.get_all(
                    request=request
                )
            else:
                template_versions = (
                    template_version_manager_api.get_all_by_user_id(
                        request=request
                    )
                )

            detailed_templates = []
            for template_version in template_versions:
                # If the version manager doesn't have a user, the template is global.
                if template_version.user is not None:
                    try:
                        username = user_api.get_user_by_id(
                            template_version.user
                        ).username
                    except ObjectDoesNotExist:
                        username = "None"

                    detailed_templates.append(
                        {
                            "template_version": template_version,
                            "template": template_api.get_by_id(
                                template_version.current, request=request
                            ),
                            "user": username,
                            "title": template_version.title,
                        }
                    )

            context = {
                "number_total": len(detailed_templates),
                "user_data": detailed_templates,
                "user_form": UserForm(request.user),
                "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.TEMPLATE.value,
                "object_name": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.TEMPLATE.value,
                "template": dashboard_constants.DASHBOARD_TEMPLATES_TEMPLATE_TABLE,
                "menu": False,
            }
            modals = [
                "core_main_app/admin/templates/list/modals/disable.html",
                EditTemplateVersionManagerView.get_modal_html_path(),
            ]

            assets = {
                "css": dashboard_constants.CSS_COMMON,
                "js": [
                    {
                        "path": "core_main_app/common/js/templates/list/restore.js",
                        "is_raw": False,
                    },
                    {
                        "path": "core_main_app/common/js/templates/list/modals/disable.js",
                        "is_raw": False,
                    },
                    {
                        "path": "core_main_app/common/js/templates/sort.js",
                        "is_raw": False,
                    },
                    {
                        "path": dashboard_constants.JS_OPEN_DOCUMENT,
                        "is_raw": False,
                    },
                    {
                        "path": "core_dashboard_common_app/common/js/list/open_template.raw.js",
                        "is_raw": True,
                    },
                    EditTemplateVersionManagerView.get_modal_js_path(),
                ],
            }

            # Set page title
            context.update({"page_title": "Dashboard"})

            return self.common_render(
                request,
                self.template,
                context=context,
                assets=assets,
                modals=modals,
            )
        except AccessControlError:
            return self.common_render(
                request,
                "core_main_app/common/commons/error.html",
                context={
                    "error": "Access Forbidden",
                    "status_code": 403,
                    "page_title": "Error",
                },
            )


class DashboardTypes(CommonView):
    """List the types."""

    template = dashboard_constants.DASHBOARD_TEMPLATE

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """

        try:
            # Get types
            if self.administration:
                type_versions = (
                    type_version_manager_api.get_all_version_manager(
                        request=request
                    )
                )
            else:
                type_versions = (
                    type_version_manager_api.get_version_managers_by_user(
                        request=request
                    )
                )

            detailed_types = []
            for type_version in type_versions:
                # If the version manager doesn't have a user, the type is global.
                if type_version.user is not None:
                    try:
                        username = user_api.get_user_by_id(
                            type_version.user
                        ).username
                    except ObjectDoesNotExist:
                        username = "None"
                    detailed_types.append(
                        {
                            "type_version": type_version,
                            "type": type_api.get(
                                type_version.current, request=request
                            ),
                            "user": username,
                            "title": type_version.title,
                        }
                    )

            context = {
                "number_total": len(detailed_types),
                "user_form": UserForm(request.user),
                "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.TYPE.value,
                "object_name": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.TYPE.value,
                "template": dashboard_constants.DASHBOARD_TYPES_TEMPLATE_TABLE,
                "menu": False,
                "user_data": detailed_types,
            }

            modals = [
                "core_main_app/admin/templates/list/modals/disable.html",
                EditTypeVersionManagerView.get_modal_html_path(),
            ]

            assets = {
                "css": dashboard_constants.CSS_COMMON,
                "js": [
                    {
                        "path": "core_main_app/common/js/templates/list/restore.js",
                        "is_raw": False,
                    },
                    {
                        "path": "core_main_app/common/js/templates/list/modals/disable.js",
                        "is_raw": False,
                    },
                    EditTypeVersionManagerView.get_modal_js_path(),
                ],
            }
            # Set page title
            context.update({"page_title": "Dashboard"})

            return self.common_render(
                request,
                self.template,
                context=context,
                assets=assets,
                modals=modals,
            )
        except AccessControlError:
            return self.common_render(
                request,
                "core_main_app/common/commons/error.html",
                context={
                    "error": "Access Forbidden",
                    "status_code": 403,
                    "page_title": "Error",
                },
            )


class DashboardWorkspaces(CommonView):
    """List the workspaces."""

    template = dashboard_constants.DASHBOARD_TEMPLATE

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """

        if self.administration:
            user_workspaces = workspace_api.get_all()
            user_workspaces_count = user_workspaces.count()
        else:
            # Get the workspace the user can read
            user_workspace_read = list(
                workspace_api.get_all_workspaces_with_read_access_by_user(
                    request.user
                )
            )
            # Get the workspace the user can write
            user_workspace_write = list(
                workspace_api.get_all_workspaces_with_write_access_by_user(
                    request.user
                )
            )
            # Get the merged list without doublons
            user_workspaces = user_workspace_read + list(
                set(user_workspace_write) - set(user_workspace_read)
            )
            user_workspaces_count = len(user_workspaces)

        detailed_user_workspaces = []
        for user_workspace in user_workspaces:
            try:
                username = (
                    user_api.get_user_by_id(user_workspace.owner).username
                    if not workspace_api.is_workspace_global(user_workspace)
                    else "GLOBAL"
                )
            except ObjectDoesNotExist:
                username = "None"
            detailed_user_workspaces.append(
                {
                    "user": username,
                    "is_owner": self.administration
                    or user_workspace.owner == str(request.user.id),
                    "name": user_workspace.title,
                    "workspace": user_workspace,
                    "can_read": self.administration
                    or user_workspace in user_workspace_read,
                    "can_write": self.administration
                    or user_workspace in user_workspace_write,
                    "is_public": workspace_api.is_workspace_public(
                        user_workspace
                    ),
                    "is_global": workspace_api.is_workspace_global(
                        user_workspace
                    ),
                    "records_count": workspace_data_api.get_all_by_workspace(
                        user_workspace, request.user
                    ).count(),
                }
            )

        context = {
            "number_total": user_workspaces_count,
            "workspace_form": WorkspaceForm(),
            "user_data": detailed_user_workspaces,
            "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.WORKSPACE.value,
            "template": dashboard_constants.DASHBOARD_WORKSPACES_TEMPLATE_TABLE,
            "create_workspace": not self.administration,
            "can_set_public": settings.CAN_SET_WORKSPACE_PUBLIC,
        }

        modals = [dashboard_constants.MODALS_COMMON_DELETE]

        assets = {
            "css": copy.deepcopy(dashboard_constants.CSS_COMMON),
            "js": [
                {
                    "path": dashboard_constants.JS_USER_SELECTED_ELEMENT,
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
            ],
        }

        if not self.administration:
            modals.append(
                "core_main_app/user/workspaces/list/create_workspace.html"
            )
            assets["js"].append(
                {
                    "path": "core_main_app/user/js/workspaces/create_workspace.js",
                    "is_raw": False,
                }
            )

        if settings.CAN_SET_WORKSPACE_PUBLIC:
            modals.append(
                "core_main_app/user/workspaces/list/modals/set_public.html"
            )
            assets["js"].append(
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/set_public.js",
                    "is_raw": False,
                }
            )
            modals.append(
                "core_main_app/user/workspaces/list/modals/set_private.html"
            )
            assets["js"].append(
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/set_private.js",
                    "is_raw": False,
                }
            )

        # Set page title
        context.update({"page_title": "Shared Workspaces"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )


class DashboardWorkspaceRecords(CommonView):
    """List the records of a workspace."""

    template = dashboard_constants.DASHBOARD_TEMPLATE
    data_template = (
        dashboard_constants.DASHBOARD_RECORDS_TEMPLATE_TABLE_PAGINATION
    )

    def get(self, request, workspace_id, *args, **kwargs):
        workspace = workspace_api.get_by_id(workspace_id)

        try:
            workspace_data = workspace_data_api.get_all_by_workspace(
                workspace, request.user
            )
        except AccessControlError:
            workspace_data = workspace_data_api.get_none()

        user_can_read = workspace_api.can_user_read_workspace(
            workspace, request.user
        )
        user_can_write = workspace_api.can_user_write_workspace(
            workspace, request.user
        )

        # Paginator
        page = request.GET.get("page", 1)
        results_paginator = ResultsPaginator.get_results(
            workspace_data, page, settings.RECORD_PER_PAGE_PAGINATION
        )

        # Data context
        try:
            results_paginator.object_list = self._format_data_context(
                results_paginator.object_list,
                request.user,
                user_can_read,
                user_can_write,
            )
        except Exception:
            results_paginator.object_list = []

        # Add user_form for change owner
        user_form = UserForm(request.user)
        context = {
            "number_total": workspace_data.count(),
            "user_data": results_paginator,
            "user_form": user_form,
            "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value,
            "template": self.data_template,
            "administration": self.administration,
            "username_list": get_id_username_dict(user_api.get_all_users()),
        }

        # Get all username and corresponding ids
        user_names = dict(
            (str(x.id), x.username) for x in user_api.get_all_users()
        )
        context.update({"usernames": user_names})
        context.update(
            {
                "title": "List of "
                + get_data_label()
                + "s of workspace: "
                + workspace.title
            }
        )

        modals = self._get_modals()

        assets = self._get_assets()

        if self.administration and workspace.owner:
            context.update(
                {
                    "owner": user_api.get_user_by_id(workspace.owner).username,
                    "owner_change_url": reverse(
                        "admin:auth_user_change", args=[workspace.owner]
                    ),
                }
            )

        # Set page title
        context.update({"page_title": "Workspace"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )

    def _format_data_context(
        self, data_list, user, user_can_read, user_can_write
    ):
        detailed_user_data = []
        for data in data_list:
            is_owner = str(data.user_id) == str(user.id) or self.administration
            detailed_user_data.append(
                {
                    "data": data,
                    "can_read": user_can_read or is_owner,
                    "can_write": user_can_write or is_owner,
                    "is_owner": is_owner,
                }
            )
        return detailed_user_data

    def _get_modals(self):
        return [
            "core_main_app/user/workspaces/list/modals/assign_workspace.html",
            dashboard_constants.MODALS_COMMON_CHANGE_OWNER,
            dashboard_constants.MODALS_COMMON_DELETE,
        ]

    def _get_assets(self):
        assets = {
            "css": copy.deepcopy(dashboard_constants.CSS_COMMON),
            "js": [
                {
                    "path": "core_main_app/user/js/workspaces/list/modals/assign_workspace.js",
                    "is_raw": False,
                },
                {
                    "path": "core_main_app/common/js/backtoprevious.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.USER_VIEW_RECORD_RAW,
                    "is_raw": True,
                },
                {"path": dashboard_constants.JS_EDIT_RECORD, "is_raw": False},
                {"path": dashboard_constants.JS_VIEW_RECORD, "is_raw": False},
                {
                    "path": dashboard_constants.JS_OPEN_DOCUMENT,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_CHANGE_OWNER,
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/open_record.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_dashboard_common_app/common/js/list/delete_data_draft.js",
                    "is_raw": False,
                },
            ],
        }

        # Admin
        if self.administration:
            assets["js"].append(
                {
                    "path": dashboard_constants.ADMIN_VIEW_RECORD_RAW,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": "core_dashboard_common_app/admin/js/action_dashboard.js",
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_COUNT_CHECK,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_RESET_CHECKBOX,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELECT_ALL,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELETED_ELEMENT,
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_INIT_MENU,
                    "is_raw": False,
                }
            )
        else:
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_USER_SELECTED_ELEMENT,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.USER_VIEW_RECORD_RAW,
                    "is_raw": True,
                }
            )

        return assets


class DashboardQueries(CommonView):
    """List the queries."""

    template = dashboard_constants.DASHBOARD_TEMPLATE
    data_template = (
        dashboard_constants.DASHBOARD_QUERIES_TEMPLATE_TABLE_PAGINATION
    )

    def get(self, request, *args, **kwargs):
        """Method GET

        Args:
            request:
            args:
            kwargs:

        Returns:
        """
        # Get all persistent queries
        persistent_query_subclasses = AbstractPersistentQuery.get_subclasses()

        items_to_render = []

        tab_selected = request.GET.get(
            "tab", persistent_query_subclasses[0].__name__
        )
        tabs = []

        for subclass in persistent_query_subclasses:
            # Get persistent query tabs
            tabs.append(subclass.__name__)

            # Get selected persistent query tab
            if tab_selected == subclass.__name__:
                query_subclass = subclass

        if self.administration:
            try:
                items_to_render = (
                    abstract_persistent_query_api.get_all_persistent_queries(
                        query_subclass, request.user
                    )
                )

            except AccessControlError:
                abstract_persistent_query_api.get_none(query_subclass)
        else:
            items_to_render = abstract_persistent_query_api.get_all_persistent_queries_by_user(
                query_subclass, request.user
            )

        # Paginator
        page = request.GET.get("page", 1)
        results_paginator = ResultsPaginator.get_results(
            items_to_render, page, settings.QUERY_PER_PAGE_PAGINATION
        )
        for result_view in ResultQueryRedirectView.__subclasses__():
            if result_view.model_name == query_subclass._meta.object_name:
                # Get query type
                url_path = result_view.get_url_path()
                query_type = result_view.object_name
                break

        try:
            detailed_query = self._get_detailed_queries(results_paginator)
        except Exception:
            detailed_query = []

        context = {
            "administration": self.administration,
            "number_total": items_to_render.count(),
            "user_data": detailed_query,
            "document": dashboard_constants.FUNCTIONAL_OBJECT_ENUM.QUERY.value,
            "template": self.data_template,
            "type": query_type,
            "url_path": url_path,
            "tab": tab_selected,
            "tabs": tabs,
            "menu": self.administration,
            "pagination": _get_pagination_document(
                page,
                results_paginator,
                items_to_render.count(),
                settings.QUERY_PER_PAGE_PAGINATION,
            ),
        }

        if self.administration:
            context.update(
                {
                    "action_form": ActionForm(
                        [("1", "Delete selected queries")]
                    ),
                }
            )

        modals = [
            dashboard_constants.MODALS_COMMON_DELETE,
            "core_main_app/common/modals/error_page_modal.html",
            "core_explore_common_app/user/persistent_query/modal.html",
            "core_dashboard_common_app/list/modals/edit_persistent_query.html",
        ]

        assets = {
            "css": dashboard_constants.CSS_COMMON,
            "js": [
                {
                    "path": "core_dashboard_common_app/user/js/init.raw.js",
                    "is_raw": True,
                },
                {
                    "path": "core_main_app/common/js/modals/error_page_modal.js",
                    "is_raw": True,
                },
                {
                    "path": dashboard_constants.JS_COMMON_FUNCTION_DELETE,
                    "is_raw": False,
                },
                {
                    "path": dashboard_constants.JS_USER_SELECTED_ELEMENT,
                    "is_raw": True,
                },
                {
                    "path": "core_main_app/user/js/sharing_modal.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/persistent_query_config.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_app/common/js/my_dashboard_tabs.js",
                    "is_raw": False,
                },
                {
                    "path": "core_dashboard_common_app/user/js/list/modals/edit_persistent_query.js",
                    "is_raw": False,
                },
            ],
        }
        assets["css"].append(
            "core_dashboard_app/common/css/my_dashboard_tabs.css"
        )
        assets["css"].append(
            "core_dashboard_common_app/common/css/content_query.css"
        )
        assets["css"].append("core_main_app/common/css/share_link.css"),

        # Admin
        if self.administration:
            assets["js"].append(
                {
                    "path": "core_dashboard_common_app/common/js/init_pagination.js",
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_ACTION_DASHBOARD,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_COUNT_CHECK,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_RESET_CHECKBOX,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELECT_ALL,
                    "is_raw": True,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_SELETED_ELEMENT,
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": dashboard_constants.JS_ADMIN_INIT_MENU,
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": "core_main_app/user/js/sharing_modal.js",
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": "core_explore_common_app/user/js/persistent_query_config.js",
                    "is_raw": False,
                }
            )
            assets["js"].append(
                {
                    "path": "core_dashboard_common_app/admin/js/my_dashboard_tabs.raw.js",
                    "is_raw": True,
                }
            )
        else:
            assets["js"].append(
                {
                    "path": "core_dashboard_common_app/user/js/my_dashboard_tabs.raw.js",
                    "is_raw": True,
                }
            )

        # Set page title
        context.update({"page_title": "Dashboard"})

        return self.common_render(
            request,
            self.template,
            context=context,
            assets=assets,
            modals=modals,
        )

    def _get_detailed_queries(self, queries):
        detailed_queries = []
        for query in queries:
            try:
                user = user_api.get_user_by_id(query.user_id)
            except ObjectDoesNotExist:
                user = None
            except ValueError:
                user = None
            detailed_queries.append({"query": query, "user": user})

        return list(reversed(detailed_queries))


def _get_pagination_document(
    page, results_paginator, number_total, document_per_page
):
    """Get pagination per document.

    Args:
        page:
        results_paginator:
        number_total:
        document_per_page:

    Returns:

    """
    # get pagination information
    previous_page_number = (
        results_paginator.previous_page_number()
        if results_paginator.has_previous()
        else None
    )
    next_page_number = (
        results_paginator.next_page_number()
        if results_paginator.has_next()
        else None
    )

    page_count = int(math.ceil(float(number_total) / document_per_page))

    # pagination has other pages?
    has_other_pages = number_total > document_per_page

    # pagination has previous?
    has_previous = previous_page_number is not None
    # pagination has next?
    has_next = next_page_number is not None and next_page_number <= page_count

    return {
        "number": int(page),
        "paginator": {"num_pages": page_count},
        "has_other_pages": has_other_pages,
        "previous_page_number": previous_page_number,
        "next_page_number": next_page_number,
        "has_previous": has_previous,
        "has_next": has_next,
    }
