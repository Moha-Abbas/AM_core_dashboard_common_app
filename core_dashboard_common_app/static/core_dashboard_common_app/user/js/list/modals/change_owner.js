/**
 * Change document owner
 */
changeOwnerDocument = function() {
    var $recordRow = $(this).closest('tr');
    var documentId = $recordRow.attr("objectid") || "";
    $('.'+functional_object+'-id').val(documentId);
    $("#banner_change_owner_errors").hide();
    $("#change-owner-modal").modal("show");

    $.ajax({
        url : loadFormChangeOwnerUrl,
        type : "POST",
        dataType: "json",
        data : {
            document_id: documentId,
            functional_object: functional_object
        },
        success: function(data){
            $("#change-owner-form-container").html(data.form);
        },
        error:function(data){
            $("#form_change_owner_errors").html(data.responseText);
            $("#banner_change_owner_errors").show(500);
        }
    });
};

/**
 * Validate fields of the change owner modal
 */
validateChangeOwner = function(){
    var errors = "";

    $("#banner_change_owner_errors").hide();
    // check if a user has been selected
    if ($( "#id_users" ).val().trim() == ""){
        errors = "Please provide a user."
    }

    if (errors != ""){
        $("#form_change_owner_errors").html(errors);
        $("#banner_change_owner_errors").show(500);
        return (false);
    }else{
        return (true);
    }
};


/**
 * AJAX call, change record owner
 */
change_owner_document = function(){
    var userId = $( "#id_users" ).val().trim();

    // A bulk change on a large selection can take a while (chunked, one
    // request per 500 records) - close the modal right away and show the
    // same full-page "please wait" overlay used elsewhere, instead of
    // leaving the modal sitting open with no feedback.
    $("#change-owner-modal").modal("hide");
    if (typeof showLoading === 'function') {
        showLoading('Changing owner, please wait...');
    }

    // Each chunk reports its own changed/skipped counts - aggregated here
    // so the user sees one final message instead of one per chunk.
    var totals = { changed: 0, skipped: 0 };

    function doChangeOwner(ids, onSuccess, onError) {
        $.ajax({
            url : dashboardChangeOwnerUrl,
            type : "POST",
            dataType: "json",
            data : {
                document_id: ids,
                user_id: userId,
                functional_object: functional_object
            },
            success: function(data){
                if (data) {
                    totals.changed += data.changed || 0;
                    totals.skipped += data.skipped || 0;
                }
                onSuccess();
            },
            error:function(data){
                if (typeof hideLoading === 'function') { hideLoading(); }
                var message = "A problem occurred while changing owner.";
                try { message = JSON.parse(data.responseText).message || message; } catch (e) {}
                $.notify(message, "danger");
                if (onError) onError();
            }
        });
    }

    function finish() {
        if (typeof hideLoading === 'function') { hideLoading(); }
        clearSelectionState();
        if (typeof queuePendingToast === 'function' && (totals.changed || totals.skipped)) {
            var text = 'Owner changed for ' + totals.changed + ' record(s).';
            if (totals.skipped) {
                text += ' ' + totals.skipped + ' could not be updated.';
            }
            queuePendingToast(text, totals.skipped ? 'warning' : 'success');
        }
        location.reload();
    }

    // If a whole chunk fails outright (rather than a partial, per-id
    // failure the backend already tolerates), stop instead of silently
    // hanging - the notification set in doChangeOwner's error handler
    // stays visible, and whatever succeeded before the failing chunk is
    // still applied server-side.
    function stop() {
        if (typeof hideLoading === 'function') { hideLoading(); }
    }

    if (typeof resolveSelectedRecordIds === 'function') {
        resolveSelectedRecordIds(function(ids) {
            submitInChunks(ids, 500, doChangeOwner, finish, stop);
        });
    } else {
        doChangeOwner(getSelectedDocument(), finish, stop);
    }
};

/**
 * Validate and change the owner
 */
validate_and_change_owner = function () {
    if (validateChangeOwner()) {
        var formData = new FormData($( "#form_start" )[0]);
        change_owner_document();
    }
};


$('.change-owner-btn').on('click', changeOwnerDocument);
$('#change-owner-yes').on('click', validate_and_change_owner);