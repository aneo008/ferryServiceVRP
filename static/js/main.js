/// Loading function when pressing restart
function loading() {
    $("#loading").show();
    $("#content").hide();
}

/// For popup message in booking.html
function popupmsg() {
    if (confirm('Do you really want delete this booking ?')) {
        $('#cover-spin').show(0)
        return true;
    } else {
        return false;
    }
}