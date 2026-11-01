(() => {
    const details = document.querySelector('.about-club details');
    if (!details) return;
    const summary = details.querySelector('summary');
    const content = details.querySelector('.about-content');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let expanded = details.open;
    let animation;

    summary.addEventListener('click', (event) => {
        event.preventDefault();
        const startHeight = details.getBoundingClientRect().height;
        animation?.cancel();
        expanded = !expanded;

        if (reducedMotion.matches) {
            details.open = expanded;
            details.classList.remove('is-animating', 'is-closing');
            return;
        }

        details.open = true;
        details.classList.add('is-animating');
        details.classList.toggle('is-closing', !expanded);
        const endHeight = summary.offsetHeight + (expanded ? content.offsetHeight : 0);
        animation = details.animate(
            { height: [`${startHeight}px`, `${endHeight}px`] },
            { duration: 280, easing: 'ease-in-out', fill: 'forwards' },
        );
        animation.onfinish = () => {
            details.open = expanded;
            animation.cancel();
            details.classList.remove('is-animating', 'is-closing');
        };
    });
})();
