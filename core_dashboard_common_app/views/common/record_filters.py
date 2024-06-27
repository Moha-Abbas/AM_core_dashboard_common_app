"""Shared filtering for the My Data records list (search / workspace / test).

Used by DashboardRecords (to render the filtered, paginated page) and by
the bulk-action "select all" id resolution endpoint, so both stay in sync.
"""


def filter_records(queryset, params):
    """Apply the search/workspace/template filters to a Data queryset.

    Args:
        queryset: Data queryset, already scoped to the requesting user.
        params: dict-like object (e.g. request.GET) with optional
            "search", "workspace", "template" keys.

    Returns:
        Filtered queryset.
    """
    search = (params.get("search") or "").strip()
    workspace_filter = (params.get("workspace") or "").strip()
    template_filter = (params.get("template") or "").strip()

    if search:
        queryset = queryset.filter(title__icontains=search)
    if workspace_filter:
        queryset = (
            queryset.filter(workspace__isnull=True)
            if workspace_filter == "none"
            else queryset.filter(workspace_id=workspace_filter)
        )
    if template_filter:
        queryset = queryset.filter(template_id=template_filter)

    return queryset
