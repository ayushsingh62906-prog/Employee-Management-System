/* ===========================================
   COLLAPSIBLE SIDEBAR
=========================================== */

const sidebar = document.querySelector(".sidebar");

const navbar = document.querySelector(".navbar");

const main = document.querySelector(".main-content");

const toggle = document.querySelector(".menu-toggle");


toggle.addEventListener("click",()=>{

    sidebar.classList.toggle("collapsed");
    sidebar.classList.toggle("show");
    navbar.classList.toggle("expanded");

    main.classList.toggle("expanded");

});
document.addEventListener("DOMContentLoaded", function () {
    const toasts = document.querySelectorAll(".toast-container .toast");
    toasts.forEach(function (toast) {
        setTimeout(function () {
            toast.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            toast.style.opacity = "0";
            toast.style.transform = "translateX(30px)";
            setTimeout(function () { toast.remove(); }, 400);
        }, 5000);
    });
});