$(document).ready(function () {
    function closeAllComboSelects() {
        $('.combo-select.open').removeClass('open');
    }

    $(document).on('click', '.combo-select-trigger', function (e) {
        e.stopPropagation();
        var $combo = $(this).closest('.combo-select');
        var isOpen = $combo.hasClass('open');
        closeAllComboSelects();
        $combo.toggleClass('open', !isOpen);
    });

    $(document).on('click', '.combo-select-option', function (e) {
        e.stopPropagation();
        var $combo = $(this).closest('.combo-select');
        var value = $(this).attr('data-value');
        var label = $(this).text().trim();

        $combo.find('input[type=hidden]').val(value);
        $combo.find('.combo-select-label').text(label);
        $combo.find('.combo-select-option').removeClass('is-selected');
        $(this).addClass('is-selected');
        $combo.removeClass('open');
    });

    $(document).on('click', function () {
        closeAllComboSelects();
    });

    $(document).on('keydown', function (e) {
        if (e.key === 'Escape') {
            closeAllComboSelects();
        }
    });
});
