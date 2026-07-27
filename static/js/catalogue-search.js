(() => {
    const search = document.getElementById('catalogue-search');
    const grid = document.getElementById('catalogue-test-grid');
    if (!search || !grid) return;
    const cards = [...grid.querySelectorAll('.catalogue-compact-card')];
    const buttons = [...document.querySelectorAll('.catalogue-part-filters [data-part]')];
    const empty = document.getElementById('catalogue-search-empty');
    let part = 'all';
    const update = () => {
        const query = search.value.trim().toLocaleLowerCase();
        let visible = 0;
        cards.forEach((card) => {
            const matches = (!query || card.dataset.title.includes(query)) && (part === 'all' || card.dataset.part === part);
            card.hidden = !matches;
            if (matches) visible += 1;
        });
        empty.hidden = visible !== 0;
    };
    search.addEventListener('input', update);
    buttons.forEach((button) => button.addEventListener('click', () => {
        part = button.dataset.part;
        buttons.forEach((item) => {
            const active = item === button;
            item.classList.toggle('is-active', active);
            item.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        update();
    }));
})();
