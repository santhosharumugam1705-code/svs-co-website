const nav = document.querySelector('.nav');
const toggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('.nav nav');

window.addEventListener('scroll', () => nav.classList.toggle('scrolled', window.scrollY > 35), { passive: true });
toggle.addEventListener('click', () => {
  const open = menu.classList.toggle('open');
  toggle.setAttribute('aria-expanded', open);
  toggle.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
});
menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  menu.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false');
}));

const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
const reveals = document.querySelectorAll('.reveal');
if (motionQuery.matches) {
  reveals.forEach(element => element.classList.add('visible'));
} else {
  const observer = new IntersectionObserver((entries) => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
  }), { threshold: .12, rootMargin: '0px 0px -28px 0px' });
  reveals.forEach(element => observer.observe(element));
}

document.querySelector('.enquiry').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = form.querySelector('.form-message');
  if (!form.checkValidity()) { message.textContent = 'Please complete the required fields before sending your enquiry.'; form.reportValidity(); return; }
  const button = form.querySelector('button');
  const data = Object.fromEntries(new FormData(form).entries());
  button.disabled = true;
  button.textContent = 'Sending...';
  message.style.color = '#526172';
  message.textContent = '';
  try {
    const response = await fetch('/api/enquiry', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message);
    message.style.color = '#16804d';
    message.textContent = result.message;
    form.reset();
  } catch (error) {
    message.style.color = '#b33c1c';
    message.textContent = error.message || 'Unable to send your enquiry. Please try again shortly.';
  } finally {
    button.disabled = false;
    button.innerHTML = 'Send Enquiry <span>&#8599;</span>';
  }
});

