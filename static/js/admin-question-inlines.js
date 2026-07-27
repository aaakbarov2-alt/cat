(function () {
    "use strict";

    function questionLabel(row, index) {
        const prompt = row.querySelector("textarea[id$='-prompt']");
        const order = row.querySelector("input[id$='-order']");
        const prefix = order && order.value ? "Question " + order.value : "New question " + (index + 1);
        if (!prompt || !prompt.value.trim()) return prefix;
        const temporary = document.createElement("div");
        temporary.innerHTML = prompt.value;
        const text = (temporary.textContent || "").trim().replace(/\s+/g, " ");
        return prefix + " — " + (text.length > 78 ? text.slice(0, 78) + "…" : text);
    }

    function prepareRow(row, index, expand) {
        if (row.dataset.compactReady || row.classList.contains("empty-form")) return;
        row.dataset.compactReady = "true";
        row.classList.add("admin-question-card");
        if (!expand) row.classList.add("is-collapsed");
        const heading = row.querySelector(":scope > h3");
        if (!heading) return;
        const original = heading.querySelector("b") || heading;
        original.textContent = questionLabel(row, index);
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "admin-question-toggle";
        toggle.setAttribute("aria-expanded", expand ? "true" : "false");
        toggle.textContent = expand ? "Collapse" : "Edit";
        toggle.addEventListener("click", function () {
            const collapsed = row.classList.toggle("is-collapsed");
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
            toggle.textContent = collapsed ? "Edit" : "Collapse";
        });
        heading.appendChild(toggle);
        const prompt = row.querySelector("textarea[id$='-prompt']");
        if (prompt) prompt.addEventListener("input", function () { original.textContent = questionLabel(row, index); });
    }

    function prepareAll() {
        document.querySelectorAll(".inline-group .inline-related").forEach(function (row, index) {
            prepareRow(row, index, !row.classList.contains("has_original") && index === 0);
        });
    }

    document.addEventListener("DOMContentLoaded", prepareAll);
    document.addEventListener("formset:added", function (event) { prepareRow(event.target, 0, true); });
})();
