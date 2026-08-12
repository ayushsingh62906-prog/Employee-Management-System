/* ===========================================
   COLLAPSIBLE SIDEBAR
=========================================== */

const sidebar = document.querySelector(".sidebar");

const navbar = document.querySelector(".navbar");

const main = document.querySelector(".main-content");

const toggle = document.querySelector(".menu-toggle");


toggle.addEventListener("click",()=>{

    sidebar.classList.toggle("collapsed");

    navbar.classList.toggle("expanded");

    main.classList.toggle("expanded");

});