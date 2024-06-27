/**
 * View record for admin.
 */

openViewRecord = function() {
    var $registryRow = $(this).closest('tr');
    var objectID = $registryRow.attr("objectid");
    var viewBtn = $(this).find( "i" );
    var icon = $(viewBtn).attr("class");

    // Show loading spinner
    showSpinner($(this).find("i"))
    $.ajax({
        url: loadRecordUrl.replace("pk", objectID),
        type: 'POST',
        contentType: 'application/json',
        success: function(response) {
            sessionStorage.setItem('data_content', JSON.stringify(response.data_content));
            sessionStorage.setItem('data_title', response.data_title);
            sessionStorage.setItem('test_id', response.test_id);
            window.location = '/gvform';
        },
        error: function(data){
            let jsonResponse = JSON.parse(data.responseText);
            $.notify(jsonResponse.error, "danger");
        }
    }).always(function() {
        hideSpinner(viewBtn, icon)
    });
};

$(".view-record-btn").on('click', openViewRecord);
