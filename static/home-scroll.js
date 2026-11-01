// Préparer le chargement avant que le navigateur ne rejoigne une ancre.
history.scrollRestoration = 'manual';
if (location.hash) {
    history.replaceState(history.state, '', location.pathname + location.search);
}

window.addEventListener('pageshow', () => {
    document.querySelector('.main-inner')?.scrollTo({ top: 0, left: 0, behavior: 'instant' });
});
