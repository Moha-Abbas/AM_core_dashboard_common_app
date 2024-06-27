""" Ajax API
"""
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.storage.base import Message
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
)
from django.urls import reverse
from django.utils.html import escape

import core_main_app.components.data.api as data_api
import core_main_app.components.template.api as template_api
import core_main_app.components.user.api as user_api
from core_explore_common_app.components.abstract_persistent_query import (
    api as persistent_query_api,
)
from core_explore_common_app.components.abstract_persistent_query.models import (
    AbstractPersistentQuery,
)
from core_main_app.access_control.exceptions import AccessControlError
from core_main_app.commons.exceptions import (
    DoesNotExist,
    NotUniqueError,
)
from core_main_app.components.blob import api as blob_api
from core_main_app.components.lock import api as lock_api
from core_main_app.components.template.models import Template
from core_main_app.components.workspace import api as workspace_api
from core_main_app.settings import INSTALLED_APPS
from core_main_app.utils.labels import get_data_label, get_form_label
from core_main_app.utils.xml import format_content_xml
from core_dashboard_common_app.views.common.forms import UserForm
from core_dashboard_common_app.views.common.record_filters import (
    filter_records,
)

if "core_curate_app" in INSTALLED_APPS:
    from core_curate_app.components.curate_data_structure.models import (
        CurateDataStructure,
    )
    import core_curate_app.components.curate_data_structure.api as curate_data_structure_api
from core_dashboard_common_app import constants


def _check_rights_document(
    request_user_is_superuser, request_user_id, document_user
):
    """Check if the user is superuser or if the document belongs to the user.

    Args:
        request_user_is_superuser:
        request_user_id:
        document_user:

    Returns:
    """
    if not request_user_is_superuser and str(request_user_id) != str(
        document_user
    ):
        raise Exception("You don't have the rights to perform this action.")


def _get_workspaces(workspace_ids, request_user_is_superuser, request_user_id):
    """Get all the workspaces from the list of ids.

    Args:
        workspace_ids:
        request_user_is_superuser:
        request_user_id:

    Returns:
        list form
    """

    list_workspaces = []
    try:
        for workspace_id in workspace_ids:
            # Get the workspace
            workspace = workspace_api.get_by_id(workspace_id)

            list_workspaces.append(workspace)
    except DoesNotExist:
        raise Exception(
            "It seems a workspace is missing. Please refresh the page."
        )
    except Exception as exception:
        raise Exception(str(exception))

    return list_workspaces


def _get_blobs(blob_ids, user):
    """Get all the blobs from the list of ids.

    Args:
        blob_ids:
        request_user_is_superuser:
        request_user_id:

    Returns:
        list form
    """

    list_blobs = []
    try:
        for blob_id in blob_ids:
            # Get the blob
            blob = blob_api.get_by_id(blob_id, user)

            # Check the rights
            _check_rights_document(user.is_superuser, user.id, blob.user_id)

            list_blobs.append(blob)
    except DoesNotExist:
        raise Exception("It seems a blob is missing. Please refresh the page.")
    except Exception as exception:
        raise Exception(str(exception))

    return list_blobs


def _get_forms(form_ids, user):
    """Get all the forms from the list of ids.

    Args:
        form_ids:
        user:

    Returns:
        list form
    """

    list_form = []
    try:
        for form_id in form_ids:
            # Get the form
            form = curate_data_structure_api.get_by_id(form_id, user)

            list_form.append(form)
    except DoesNotExist:
        raise Exception(
            "It seems a "
            + get_form_label()
            + " is missing. Please refresh the page."
        )
    except Exception as exception:
        raise Exception(str(exception))

    return list_form


def _get_data(data_ids, user):
    """Get all the data from the list of ids.

    Args:
        data_ids:
        user:

    Returns:
        data table
    """

    data_table = []
    try:
        for data_id in data_ids:
            # Get the data
            data = data_api.get_by_id(data_id, user)

            # Check the rights
            _check_rights_document(
                user.is_superuser, str(user.id), data.user_id
            )

            data_table.append(data)
    except DoesNotExist:
        raise Exception(
            "It seems a "
            + get_data_label()
            + " is missing. Please refresh the page."
        )
    except Exception as exception:
        raise Exception(str(exception))

    return data_table


def _get_query(query_type, query_ids, user):
    """Get all the persistent queries from the list of ids.

    Args:
        query_type:
        query_ids:
        user:

    Returns:
        data table
    """

    query_table = []
    try:
        for query_id in query_ids:
            # Get the persistent query
            query = persistent_query_api.get_by_id(query_type, query_id, user)

            # Check the rights
            _check_rights_document(
                user.is_superuser, str(user.id), query.user_id
            )

            query_table.append(query)
    except DoesNotExist:
        raise Exception(
            "It seems a query is missing. Please refresh the page."
        )
    except Exception as exception:
        raise Exception(str(exception))

    return query_table


# FIXME: fix error message
@login_required
def delete_document(request):
    """Delete a document (record or form).

    Args:
        request:

    Returns:
    """
    document = request.POST["functional_object"]

    document_ids = request.POST.getlist("document_id[]", [])
    is_record = document == constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value
    if (
        len(document_ids) > 1
        and not request.user.is_superuser
        and not is_record
    ):
        return HttpResponseServerError(
            {"You don't have the rights to perform this action."}, status=403
        )

    if document == constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value:
        return _delete_record(request, document_ids)
    if document == constants.FUNCTIONAL_OBJECT_ENUM.FORM.value:
        return _delete_form(request, document_ids)
    if document == constants.FUNCTIONAL_OBJECT_ENUM.FILE.value:
        return _delete_file(request, document_ids)
    if document == constants.FUNCTIONAL_OBJECT_ENUM.QUERY.value:
        return _delete_query(request, document_ids)
    if document == constants.FUNCTIONAL_OBJECT_ENUM.WORKSPACE.value:
        return _delete_workspace(request, document_ids)

    return HttpResponseBadRequest(
        {"Bad entries. Please check the parameters."}
    )


def _delete_workspace(request, workspace_ids):
    """Delete workspace.

    Args:
        request:
        workspace_ids:

    Returns:
    """
    try:
        list_workspaces = _get_workspaces(
            workspace_ids, request.user.is_superuser, request.user.id
        )
    except Exception as exception:
        messages.add_message(request, messages.ERROR, str(exception))
        return HttpResponse(
            json.dumps({}), content_type="application/javascript"
        )

    try:
        for workspace in list_workspaces:
            workspace_api.delete(workspace, request.user)
    except AccessControlError as ace:
        return HttpResponseBadRequest(escape(str(ace)))

    return HttpResponse(json.dumps({}), content_type="application/javascript")


def _delete_file(request, blob_ids):
    """Delete blobs.

    Args:
        request:
        blob_ids:

    Returns:
    """
    try:
        list_blob = _get_blobs(blob_ids, request.user)
    except Exception as exception:
        messages.add_message(request, messages.ERROR, str(exception))
        return HttpResponse(
            json.dumps({}), content_type="application/javascript"
        )

    try:
        for blob in list_blob:
            blob_api.delete(blob, request.user)
        messages.add_message(request, messages.SUCCESS, "File deleted.")
    except Exception:
        messages.add_message(
            request, messages.ERROR, "A problem occurred while deleting."
        )

    return HttpResponse(json.dumps({}), content_type="application/javascript")


def _delete_form(request, form_ids):
    """Delete forms.

    Args:
        request:
        form_ids:

    Returns:
    """
    try:
        list_form = _get_forms(form_ids, request.user)
    except Exception as exception:
        messages.add_message(request, messages.ERROR, str(exception))
        return HttpResponse(
            json.dumps({}), content_type="application/javascript"
        )

    try:
        for form in list_form:
            curate_data_structure_api.delete(form, request.user)
        messages.add_message(
            request,
            messages.SUCCESS,
            get_form_label().capitalize() + " deleted.",
        )
    except Exception:
        messages.add_message(
            request, messages.ERROR, "A problem occurred while deleting."
        )

    return HttpResponse(json.dumps({}), content_type="application/javascript")


def _delete_record(request, data_ids):
    """Delete records.

    Each id is resolved and deleted independently, so a single stale/
    missing/locked id in a bulk selection doesn't silently abort deletion
    of the rest of the batch (previously, fetching all records up front
    meant one bad id made the whole request a no-op that still reported
    success to the browser).

    Args:
        request:
        data_ids:

    Returns:
    """

    deleted_count = 0
    skipped_count = 0

    for data_id in data_ids:
        try:
            data = data_api.get_by_id(data_id, request.user)
            _check_rights_document(
                request.user.is_superuser, str(request.user.id), data.user_id
            )

            if lock_api.is_object_locked(data.id, request.user):
                skipped_count += 1
                continue

            data_api.delete(data, request.user)
            deleted_count += 1
        except Exception:
            skipped_count += 1

    label = get_data_label()
    if deleted_count == 0:
        return HttpResponseBadRequest(
            json.dumps(
                {
                    "message": "Unable to delete: the selected "
                    + label
                    + "(s) could not be found, are locked, or you don't "
                    "have the rights to delete them. Please refresh the "
                    "page and try again."
                }
            ),
            content_type="application/javascript",
        )

    # No django `messages` added here: a bulk delete over a large
    # selection is sent as several chunked requests (one per 500 ids), and
    # each one hitting this view separately would each queue its own
    # message, so the user'd see them all pile up on reload ("500
    # deleted", then "31 deleted", ...). The client aggregates the
    # deleted/skipped counts from every chunk's response below and shows
    # a single consolidated notification once the whole batch is done.
    return HttpResponse(
        json.dumps({"deleted": deleted_count, "skipped": skipped_count}),
        content_type="application/javascript",
    )


def _delete_query(request, query_ids):
    """Delete query.

    Args:
        request:
        query_ids:

    Returns:
    """

    try:
        # Get persistent query class name
        persistent_query_type = request.POST["document_type"]

        # Get  persistent query document
        persistent_query_class = next(
            (
                subclass
                for subclass in AbstractPersistentQuery.get_subclasses()
                if subclass.__name__ == persistent_query_type
            ),
            None,
        )

        # Get the persistent queries
        list_query = _get_query(
            persistent_query_class, query_ids, request.user
        )

    except Exception as exception:
        messages.add_message(request, messages.ERROR, str(exception))
        return HttpResponse(
            json.dumps({}), content_type="application/javascript"
        )

    try:
        for query in list_query:
            persistent_query_api.delete(query, request.user)

        messages.add_message(
            request,
            messages.SUCCESS,
            " Query deleted.",
        )
    except Exception:
        messages.add_message(
            request, messages.ERROR, "A problem occurred while deleting."
        )

    return HttpResponse(json.dumps({}), content_type="application/javascript")


@login_required
def load_form_change_owner(request):
    """Load the change-owner form for a single document, with its current
    owner preselected.

    Args:
        request:

    Returns:
    """
    document_id = request.POST.get("document_id")
    functional_object = request.POST.get("functional_object")

    if not functional_object:
        return HttpResponseBadRequest(
            {"Bad entries. Please check the parameters."}
        )

    # document_id is only present for a single-record action; a bulk
    # change-owner has no single current owner to preselect, so the form
    # falls back to its default blank choice.
    current_owner_id = None
    if document_id:
        try:
            if (
                functional_object
                == constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value
            ):
                current_owner_id = data_api.get_by_id(
                    document_id, request.user
                ).user_id
            elif (
                functional_object
                == constants.FUNCTIONAL_OBJECT_ENUM.FILE.value
            ):
                current_owner_id = blob_api.get_by_id(
                    document_id, request.user
                ).user_id
            elif (
                functional_object
                == constants.FUNCTIONAL_OBJECT_ENUM.FORM.value
                and "core_curate_app" in INSTALLED_APPS
            ):
                current_owner_id = curate_data_structure_api.get_by_id(
                    document_id, request.user
                ).user_id
        except Exception:
            # Owner can't be resolved (e.g. no access) - the form falls
            # back to its default blank choice.
            current_owner_id = None

    form = UserForm(request.user, current_owner_id)

    return HttpResponse(
        json.dumps(
            {
                "form": loader.render_to_string(
                    "core_dashboard_common_app/list/modals/change_owner_form.html",
                    {"user_form": form},
                )
            }
        ),
        content_type="application/javascript",
    )


@login_required
def get_record_ids(request):
    """Return all record ids owned by the user (matching the current
    search/workspace/test filters), used to resolve a cross-page
    "select all" on the My Data page into a concrete id list.

    Args:
        request:

    Returns:
    """
    if request.GET.get("administration") == "True" and request.user.is_superuser:
        try:
            queryset = data_api.get_all(request.user)
        except AccessControlError:
            queryset = data_api.get_none()
    else:
        queryset = data_api.get_all_by_user(request.user)

    queryset = filter_records(queryset, request.GET)
    ids = list(
        queryset.order_by().values_list("id", flat=True).distinct()
    )

    return HttpResponse(
        json.dumps({"ids": [str(record_id) for record_id in ids]}),
        content_type="application/javascript",
    )


@login_required
def change_owner_document(request):
    """Change owner of a document (record or form).

    Args:
        request:

    Returns:
    """

    if (
        "document_id[]" in request.POST
        and "user_id" in request.POST
        and "functional_object" in request.POST
    ):
        document = request.POST["functional_object"]
        user_id = request.POST["user_id"]

        document_ids = request.POST.getlist("document_id[]", [])
        is_record = document == constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value
        if (
            len(document_ids) > 1
            and not request.user.is_superuser
            and not is_record
        ):
            return HttpResponseServerError(
                {"You don't have the rights to perform this action."},
                status=403,
            )

        if document == constants.FUNCTIONAL_OBJECT_ENUM.RECORD.value:
            return _change_owner_record(request, document_ids, user_id)
        if document == constants.FUNCTIONAL_OBJECT_ENUM.FORM.value:
            return _change_owner_form(request, document_ids, user_id)
        if document == constants.FUNCTIONAL_OBJECT_ENUM.FILE.value:
            return _change_owner_file(request, document_ids, user_id)

    else:
        return HttpResponseBadRequest(
            {"Bad entries. Please check the parameters."}
        )

    return HttpResponse(json.dumps({}), content_type="application/javascript")


def _change_owner_form(request, form_ids, user_id):
    """Change the owner of a form.

    Args:
        request:
        form_ids:
        user_id:

    Returns:
    """
    try:
        list_form = _get_forms(form_ids, request.user)
    except Exception as exception:
        return HttpResponseBadRequest(escape(str(exception)))

    try:
        new_user = user_api.get_user_by_id(user_id)
        failed_draft = 0
        for form in list_form:
            try:
                curate_data_structure_api.change_owner(
                    form, new_user, request.user
                )
            except Exception:
                failed_draft += 1
        if failed_draft > 0:
            error_message = (
                f"Unable to change owner for {failed_draft} document(s)"
            )
            messages.add_message(request, messages.WARNING, error_message)
    except Exception as exception:
        return HttpResponseBadRequest(escape(str(exception)))

    return HttpResponse(json.dumps({}), content_type="application/javascript")


def _change_owner_record(request, data_ids, user_id):
    """Change the owner of records.

    Each id is resolved and updated independently, so a single stale/
    missing/inaccessible id in a bulk selection doesn't abort the change
    for the rest of the batch.

    Args:
        request:
        data_ids:
        user_id:

    Returns:
    """
    try:
        new_user = user_api.get_user_by_id(user_id)
    except Exception as exception:
        return HttpResponseBadRequest(escape(str(exception)))

    changed_count = 0
    skipped_count = 0
    for data_id in data_ids:
        try:
            data = data_api.get_by_id(data_id, request.user)
            data_api.change_owner(data, new_user, request.user)
            changed_count += 1
        except Exception:
            skipped_count += 1

    label = get_data_label()
    if changed_count == 0:
        return HttpResponseBadRequest(
            json.dumps(
                {
                    "message": "Unable to change owner: the selected "
                    + label
                    + "(s) could not be found or you don't have the "
                    "rights to change them. Please refresh the page and "
                    "try again."
                }
            ),
            content_type="application/javascript",
        )

    # No django `messages` added here - see the matching note in
    # _delete_record: a large selection is sent in chunks, and the client
    # aggregates deleted/skipped counts across all of them into a single
    # notification instead of one per chunk.
    return HttpResponse(
        json.dumps({"changed": changed_count, "skipped": skipped_count}),
        content_type="application/javascript",
    )


def _change_owner_file(request, blob_ids, user_id):
    """Change the owner of a record.

    Args:
        request:
        blob_ids:
        user_id:

    Returns:
    """
    try:
        list_blob = _get_blobs(blob_ids, request.user)
    except Exception as exception:
        return HttpResponseBadRequest(escape(str(exception)))
    try:
        new_user = user_api.get_user_by_id(user_id)
        for blob in list_blob:
            blob_api.change_owner(blob, new_user, request.user)
    except Exception as exception:
        return HttpResponseBadRequest(escape(str(exception)))

    return HttpResponse(json.dumps({}), content_type="application/javascript")


@login_required
def edit_record(request):
    """Edit a record.

    Args:
        request:

    Returns:
    """
    try:
        data = data_api.get_by_id(request.POST["id"], request.user)
    except DoesNotExist:
        message = Message(
            messages.ERROR,
            "It seems a "
            + get_data_label()
            + " is missing. Please refresh the page.",
        )
        return HttpResponseBadRequest(
            json.dumps({"message": message.message, "tags": message.tags}),
            content_type="application/json",
        )

    # Check if the data is locked
    if lock_api.is_object_locked(data.id, request.user):
        message = Message(
            messages.ERROR,
            "The " + get_data_label() + " is locked. You can't edit it.",
        )
        return HttpResponseBadRequest(
            json.dumps({"message": message.message, "tags": message.tags}),
            content_type="application/json",
        )
    # Check if XSD or JSON format data
    if data.template.format not in [Template.XSD, Template.JSON]:
        message = Message(
            messages.ERROR,
            f"Unable to edit  {get_data_label()}. This feature is only available for XML and JSON {get_data_label()} ",
        )
        return HttpResponseBadRequest(
            json.dumps({"message": message.message, "tags": message.tags}),
            content_type="application/json",
        )
    try:
        # Check if a curate data structure already exists
        curate_data_structure = (
            curate_data_structure_api.get_by_data_id_and_user(
                data.id, request.user
            )
        )
    except DoesNotExist:
        try:
            template = template_api.get_by_id(
                str(data.template.id), request=request
            )
        except AccessControlError:
            message = Message(
                messages.ERROR,
                "Unable to access the template for this data: Access forbidden.",
            )
            return HttpResponseBadRequest(
                json.dumps({"message": message.message, "tags": message.tags}),
                content_type="application/json",
            )
        # Create a new curate data structure
        curate_data_structure = CurateDataStructure(
            user=str(request.user.id),
            template=template,
            name=data.title,
            form_string=data.content,
            data=data,
        )
        try:
            curate_data_structure = curate_data_structure_api.upsert(
                curate_data_structure, request.user
            )
        except NotUniqueError:
            message = Message(
                messages.ERROR,
                f"Unable to edit the {get_data_label()}. Please check that a {get_form_label()}"
                f" with the same name does not already exist.",
            )
            return HttpResponseBadRequest(
                json.dumps({"message": message.message, "tags": message.tags}),
                content_type="application/json",
            )
        except Exception:
            message = Message(
                messages.ERROR,
                f"An unexpected error occurred. Unable to edit the {get_data_label()}.",
            )
            return HttpResponseBadRequest(
                json.dumps({"message": message.message, "tags": message.tags}),
                content_type="application/json",
            )

    except Exception:
        message = Message(messages.ERROR, "A problem occurred while editing.")
        return HttpResponseBadRequest(
            json.dumps({"message": message.message, "tags": message.tags}),
            content_type="application/json",
        )
    

    data_id = data.id
    data_content = data.content
    data_title = data.title
    data_template = data.template_id

    data_content = format_content_xml(data_content)

    # Store data in session
    request.session['edit_record_data'] = {
        'data_id': data_id,
        'data_content': data_content,
        'data_title': data_title,
        'test_id' :  data_template,
        'edit': True
    }

    return JsonResponse({
        'url': '/gvform/edit'
    })
