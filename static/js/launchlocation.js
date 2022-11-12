$(document).ready(function () {
    setInterval(function () {
        $("#launch").load(location.href + " #launch");
        $("img").each(function () {
            var url = $(this).attr("src");
            $(this).removeAttr("src").attr("src", url);
        })
    }, 1000);
});