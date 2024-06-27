var MODIFY_MODE_KEY = 'records-modify-mode-on';

function loadModifyModeOn() {
    try {
        return sessionStorage.getItem(MODIFY_MODE_KEY) === '1';
    } catch (e) {
        return false;
    }
}

function saveModifyModeOn(on) {
    try {
        if (on) {
            sessionStorage.setItem(MODIFY_MODE_KEY, '1');
        } else {
            sessionStorage.removeItem(MODIFY_MODE_KEY);
        }
    } catch (e) {}
}

// If the previous page wasn't this same records page (i.e. the user
// navigated in from elsewhere rather than paginating/filtering within it),
// drop any leftover Modify Records mode/selection from a prior visit.
function clearRecordsSessionStateIfLeftPage() {
    try {
        var cameFromSamePage = false;
        if (document.referrer) {
            var referrerPath = new URL(document.referrer).pathname;
            cameFromSamePage = referrerPath === window.location.pathname;
        }
        if (cameFromSamePage) {
            return;
        }
        var keysToRemove = [];
        for (var i = 0; i < sessionStorage.length; i++) {
            var key = sessionStorage.key(i);
            if (key === MODIFY_MODE_KEY || key.indexOf('records-selection:') === 0) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(function (key) { sessionStorage.removeItem(key); });
    } catch (e) {}
}

function currentFilterParams() {
    var params = new URLSearchParams(window.location.search);
    // `menu` (declared in init.raw.js from data.menu / self.administration)
    // is the actual admin-vs-my-data flag - there never was a variable
    // literally named `administration`, so this always silently sent
    // "False" to the server, even from the admin ("all records") view.
    // That made "select all" resolve ids via get_all_by_user() instead of
    // get_all(), so an admin whose selection included records they don't
    // personally own would get 0 ids back and the bulk action would
    // silently do nothing.
    return {
        search: params.get('search') || '',
        workspace: params.get('workspace') || '',
        template: params.get('template') || '',
        administration: (typeof menu !== 'undefined' && menu) ? 'True' : 'False'
    };
}

function recordsSelectionKey() {
    var p = currentFilterParams();
    return 'records-selection:' + p.search + '|' + p.workspace + '|' + p.template + '|' + p.administration;
}

function loadSelectionState() {
    try {
        var raw = sessionStorage.getItem(recordsSelectionKey());
        if (raw) {
            var parsed = JSON.parse(raw);
            return {
                allSelected: !!parsed.allSelected,
                selectedIds: parsed.selectedIds || [],
                excludedIds: parsed.excludedIds || []
            };
        }
    } catch (e) {}
    return { allSelected: false, selectedIds: [], excludedIds: [] };
}

function saveSelectionState(state) {
    try {
        sessionStorage.setItem(recordsSelectionKey(), JSON.stringify(state));
    } catch (e) {}
}

function clearSelectionState() {
    try {
        sessionStorage.removeItem(recordsSelectionKey());
    } catch (e) {}
}

function applySelectionStateToPage(state) {
    $('*[id^="actionCheckbox"] input[type=checkbox]').each(function () {
        var id = String(this.id);
        var checked = state.allSelected
            ? state.excludedIds.indexOf(id) === -1
            : state.selectedIds.indexOf(id) !== -1;
        $(this).prop('checked', checked);
    });
    $('[id^="select_all_"]').prop('checked', state.allSelected);
}

function updateSelectedRecordsCount() {
    var state = loadSelectionState();
    var n = state.allSelected
        ? Math.max(recordsTotalCount - state.excludedIds.length, 0)
        : state.selectedIds.length;

    $('#modify-selected-count').text(n + (n === 1 ? ' record selected' : ' records selected'));

    var dropdownBtn = document.getElementById('dropdownMenu1');
    if (dropdownBtn) {
        dropdownBtn.disabled = n === 0;
    }
}

// Resolves the ids a bulk action should apply to: a single row's id (legacy
// single-record flow), the persisted cross-page selection, or - if "select
// all" spans every page - the full matching set fetched from the server
// (minus anything explicitly excluded).
function resolveSelectedRecordIds(callback) {
    var singleId = $('.' + functional_object + '-id').val();
    if (singleId) {
        callback([singleId]);
        return;
    }

    var state = loadSelectionState();
    if (!state.allSelected) {
        callback(state.selectedIds.slice());
        return;
    }

    // The server sends this JSON body with Content-Type: application/javascript
    // (a long-standing convention elsewhere in this codebase) - jQuery's
    // dataType auto-detection treats that as a script to execute, not JSON
    // to parse, so `data` here would silently NOT be the {ids: [...]} object
    // without forcing dataType explicitly. That's why "select all" always
    // resolved to zero ids and every bulk action on it silently did nothing.
    $.get(recordIdsUrl, currentFilterParams(), function (data) {
        var excluded = {};
        (state.excludedIds || []).forEach(function (id) { excluded[id] = true; });
        var ids = (data.ids || []).filter(function (id) { return !excluded[id]; });
        callback(ids);
    }, 'json').fail(function () {
        callback([]);
    });
}

function applyModifyModeVisual(on) {
    $('#records-modify-wrapper').toggleClass('modify-mode-on', on);
    $('#toggle-modify-records').toggleClass('active', on);
    $('#toggle-modify-records-label').text(on ? 'Done' : 'Modify Records');
    $('#toggle-modify-records-icon')
        .toggleClass('fa-list-check', !on)
        .toggleClass('fa-xmark', on);
}

// Splits a (possibly very large) id list into sequential requests so a
// single bulk action never sends more ids than Django's POST field limit
// allows.
function submitInChunks(ids, chunkSize, requestFn, onDone, onError) {
    if (!ids || ids.length === 0) {
        onDone();
        return;
    }
    var chunks = [];
    for (var i = 0; i < ids.length; i += chunkSize) {
        chunks.push(ids.slice(i, i + chunkSize));
    }
    function next(index) {
        if (index >= chunks.length) {
            onDone();
            return;
        }
        requestFn(chunks[index], function () {
            next(index + 1);
        }, onError);
    }
    next(0);
}

$(document).ready(function () {
    clearRecordsSessionStateIfLeftPage();
    applyModifyModeVisual(loadModifyModeOn());
    applySelectionStateToPage(loadSelectionState());
    updateSelectedRecordsCount();

    $(document).on('change', '*[id^="actionCheckbox"] input[type=checkbox]', function () {
        var id = String(this.id);
        var checked = this.checked;
        var state = loadSelectionState();

        if (state.allSelected) {
            var idx = state.excludedIds.indexOf(id);
            if (checked && idx !== -1) {
                state.excludedIds.splice(idx, 1);
            } else if (!checked && idx === -1) {
                state.excludedIds.push(id);
            }
        } else {
            var sIdx = state.selectedIds.indexOf(id);
            if (checked && sIdx === -1) {
                state.selectedIds.push(id);
            } else if (!checked && sIdx !== -1) {
                state.selectedIds.splice(sIdx, 1);
            }
        }

        saveSelectionState(state);
        updateSelectedRecordsCount();
    });

    $(document).on('change', '[id^="select_all_"]', function () {
        var state = this.checked
            ? { allSelected: true, selectedIds: [], excludedIds: [] }
            : { allSelected: false, selectedIds: [], excludedIds: [] };

        saveSelectionState(state);
        applySelectionStateToPage(state);
        updateSelectedRecordsCount();
    });

    function setModifyMode(on) {
        applyModifyModeVisual(on);
        saveModifyModeOn(on);

        if (!on) {
            clearSelectionState();
            applySelectionStateToPage({ allSelected: false, selectedIds: [], excludedIds: [] });
            $('.' + functional_object + '-id').val('');
        }
        updateSelectedRecordsCount();
    }

    $('#toggle-modify-records').on('click', function () {
        setModifyMode(!$('#records-modify-wrapper').hasClass('modify-mode-on'));
    });
});
