console.log('Script is running');
document.addEventListener('DOMContentLoaded', () => {
    const svgIcons = document.querySelectorAll('.MuiSvgIcon-root');
    console.log('nice');
    svgIcons.forEach(svg => {
        svg.addEventListener('click', function() {
            console.log('SVG clicked'); // Debugging message
            this.classList.toggle('active'); // Toggle 'active' class on click
        });
    });
});


