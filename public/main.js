document.addEventListener('DOMContentLoaded', (event) => {
    const themeSwitch = document.querySelector('input[name="switch-theme"]');
    if (themeSwitch) {
        themeSwitch.checked = true; // Turn on dark mode
        themeSwitch.dispatchEvent(new Event('change'));
    }
});
