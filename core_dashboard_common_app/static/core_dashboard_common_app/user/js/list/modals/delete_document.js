
/**
 * Work out how many records are about to be deleted, so the confirmation
 * modal can say "record" vs "records" correctly. A single row click always
 * means 1; a bulk action (no row context) means whatever is selected.
 * @param singleId id of the row that was clicked, or undefined/empty for a bulk action
 * @returns {number}
 */
function getDeleteCandidateCount(singleId) {
    if (singleId) {
        return 1;
    }
    if (typeof loadSelectionState !== 'function') {
        return 1;
    }
    var state = loadSelectionState();
    if (state.allSelected) {
        var total = typeof recordsTotalCount !== 'undefined' ? recordsTotalCount : 0;
        return Math.max(total - state.excludedIds.length, 0);
    }
    return state.selectedIds.length;
}

/**
 * Open the modal before deleting the document
 */
openDeleteDocument = function () {
    var $recordRow = $(this).closest('tr');
    var singleId = $recordRow.attr("objectid");
    $('.'+functional_object+'-id').val(singleId);
    $("#delete_banner_errors").hide();

    var count = getDeleteCandidateCount(singleId);
    var word = count === 1 ? $('#delete-modal-singular').val() : $('#delete-modal-plural').val();
    if (word) {
        $('#delete-modal-word, #delete-modal-word-body').text(word);
    }

    $("#delete-result-modal").modal("show");
};

/**
 * AJAX call, delete a curated document
 * @param result_id
 */
delete_document = function(){
    var icon = $("[id^='delete-document-yes'] > i").attr("class");
    // Show loading spinner
    showSpinner($("[id^='delete-document-yes'] > i"))

    // A bulk delete on a large selection can take a while (chunked, one
    // request per 500 records) - close the confirmation dialog right away
    // and show the same full-page "please wait" overlay used elsewhere,
    // instead of leaving the modal sitting open with just a small spinner
    // on the button.
    $("#delete-result-modal").modal("hide");
    if (typeof showLoading === 'function') {
        showLoading('Deleting, please wait...');
    }

    var documentType = $('.nav-tabs .active').attr("title");
    // Each chunk reports its own deleted/skipped counts - aggregated here
    // so the user sees one final message instead of one per chunk.
    var totals = { deleted: 0, skipped: 0 };

    function doDelete(ids, onSuccess, onError) {
        $.ajax({
            url : dashboardDeleteDocumentUrl,
            type : "POST",
            dataType: "json",
            data : {
                document_id: ids,
                functional_object: functional_object,

                // get query class name
                document_type: documentType

            },
            success: function(data){
                if (data) {
                    totals.deleted += data.deleted || 0;
                    totals.skipped += data.skipped || 0;
                }
                onSuccess();
            },
            error:function(data){
                if (typeof hideLoading === 'function') { hideLoading(); }
                let error_message = JSON.parse(data.responseText);
                $.notify(error_message.message, "danger");
                if (onError) onError();
            }
        });
    }

    function finish() {
        hideSpinner($("[id^='delete-document-yes'] > i"), icon);
        if (typeof hideLoading === 'function') { hideLoading(); }
        if (typeof clearSelectionState === 'function') {
            clearSelectionState();
        }
        if (typeof queuePendingToast === 'function' && (totals.deleted || totals.skipped)) {
            var word = totals.deleted === 1 ? $('#delete-modal-singular').val() : $('#delete-modal-plural').val();
            var text = totals.deleted + ' ' + (word || 'record(s)') + ' deleted.';
            if (totals.skipped) {
                text += ' ' + totals.skipped + ' could not be deleted.';
            }
            queuePendingToast(text, totals.skipped ? 'warning' : 'success');
        }
        location.reload();
    }

    function stop() {
        hideSpinner($("[id^='delete-document-yes'] > i"), icon);
        if (typeof hideLoading === 'function') { hideLoading(); }
    }

    if (typeof resolveSelectedRecordIds === 'function') {
        resolveSelectedRecordIds(function(ids) {
            submitInChunks(ids, 500, doDelete, finish, stop);
        });
    } else {
        doDelete(getSelectedDocument(), finish, stop);
    }
};


$('.delete-document-btn').on('click', openDeleteDocument);
$('#delete-document-yes').on('click', delete_document);
