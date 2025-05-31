let currentIndex = 0;
const slides = document.querySelector(".slides");
const dots = document.querySelectorAll(".nav-dot");

function currentSlide(index) {
  currentIndex = index - 1;
  updateSlider();
}

function updateSlider() {
  slides.style.transform = `translateX(-${currentIndex * 100}%)`;
  dots.forEach((dot, i) => {
    dot.classList.toggle("active", i === currentIndex);
  });
}

setInterval(() => {
  currentIndex = (currentIndex + 1) % 3;
  updateSlider();
}, 5000);
