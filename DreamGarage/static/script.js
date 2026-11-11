// ==============================
// DREAMGARAGE - main.js
// ==============================

// Navbar Scroll Effect
const navbar = document.getElementById("navbar");

window.addEventListener("scroll", () => {
    if (window.scrollY > 50) {
        navbar.classList.add("scrolled");
    } else {
        navbar.classList.remove("scrolled");
    }
});

// Mobile Menu
const hamburger = document.getElementById("hamburger");
const navLinks = document.getElementById("navLinks");

if (hamburger) {
    hamburger.addEventListener("click", () => {
        navLinks.classList.toggle("open");
    });
}

// Close menu after clicking link
document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", () => {
        navLinks.classList.remove("open");
    });
});

// ==============================
// Scroll Animation
// ==============================

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add("visible");
        }
    });
}, {
    threshold: 0.2
});

document.querySelectorAll(".car-card, .step, .testi-card").forEach(item => {
    observer.observe(item);
});

// ==============================
// Color Preview
// ==============================

const swatches = document.querySelectorAll(".swatch");
const gradStart = document.getElementById("gradStart");
const gradEnd = document.getElementById("gradEnd");
const colorLabel = document.getElementById("colorLabel");

swatches.forEach(swatch => {

    swatch.addEventListener("click", () => {

        swatches.forEach(s => s.classList.remove("active"));
        swatch.classList.add("active");

        const color = swatch.style.background;
        const name = swatch.getAttribute("title");

        if (gradStart) {
            gradStart.setAttribute("style", `stop-color:${color}`);
        }

        if (gradEnd) {
            gradEnd.setAttribute("style", `stop-color:${color}`);
        }

        if (colorLabel) {
            colorLabel.textContent = name;
        }

    });

});

// ==============================
// Smooth Scroll
// ==============================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {

    anchor.addEventListener("click", function(e) {

        e.preventDefault();

        const target = document.querySelector(this.getAttribute("href"));

        if (target) {
            target.scrollIntoView({
                behavior: "smooth"
            });
        }

    });

});

// ==============================
// Hero Car Floating Animation
// ==============================

const heroCar = document.querySelector(".hero-car-visual");

if (heroCar) {

    let offset = 0;

    setInterval(() => {

        offset += 0.02;

        heroCar.style.transform =
            `translateY(${Math.sin(offset) * 8}px)`;

    }, 20);

}