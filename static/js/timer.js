/// Timer function, to show the time
$(document).ready(function () {
    intervalID = setInterval(function () {
        $("#printtimenow").load(location.href + " #printtimenow");
    }, 2000);
});

function stop() {
    clearInterval(intervalID)
};

document.getElementById("restart").addEventListener("click", stop);
document.getElementById("delete").forEach(this.addEventListener("click", stop));
document.getElementById("submit").addEventListener("click", stop);