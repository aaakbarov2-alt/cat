(function () {
    "use strict";

    const controls = [
        ["formatBlock", "H2", "Heading", "h2"],
        ["formatBlock", "H3", "Subheading", "h3"],
        ["bold", "B", "Bold"],
        ["italic", "I", "Italic"],
        ["underline", "U", "Underline"],
        ["insertUnorderedList", "• List", "Bullet list"],
        ["insertOrderedList", "1. List", "Numbered list"],
        ["formatBlock", "❝", "Quotation", "blockquote"],
        ["createLink", "Link", "Insert link"],
        ["undo", "↶", "Undo"],
        ["redo", "↷", "Redo"],
        ["removeFormat", "Clear", "Clear formatting"],
    ];

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;
    }

    function initialHtml(value) {
        if (/<\/?(?:p|br|strong|em|u|h2|h3|ul|ol|li|blockquote|a)\b/i.test(value)) return value;
        return value.split(/\n{2,}/).filter(Boolean).map(function (part) {
            return "<p>" + escapeHtml(part).replace(/\n/g, "<br>") + "</p>";
        }).join("");
    }

    function createButton(command, label, title, value, editor) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "admin-rich-text__button";
        button.textContent = label;
        button.title = title;
        button.setAttribute("aria-label", title);
        button.addEventListener("mousedown", function (event) { event.preventDefault(); });
        button.addEventListener("click", function () {
            editor.focus();
            let commandValue = value || null;
            if (command === "createLink") {
                commandValue = window.prompt("Enter the link address (https://...)");
                if (!commandValue) return;
            }
            document.execCommand(command, false, commandValue);
            editor.dispatchEvent(new Event("input", { bubbles: true }));
        });
        return button;
    }

    function enhance(textarea) {
        if (textarea.dataset.editorReady) return;
        textarea.dataset.editorReady = "true";
        const shell = document.createElement("div");
        shell.className = "admin-rich-text";
        const editorKind = textarea.dataset.richTextEditor || "text";
        shell.classList.add("admin-rich-text--" + editorKind);
        const toolbar = document.createElement("div");
        toolbar.className = "admin-rich-text__toolbar";
        toolbar.setAttribute("role", "toolbar");
        toolbar.setAttribute("aria-label", editorKind === "prompt" ? "Question prompt formatting tools" : "Passage formatting tools");
        const editor = document.createElement("div");
        editor.className = "admin-rich-text__editor";
        editor.contentEditable = "true";
        editor.setAttribute("role", "textbox");
        editor.setAttribute("aria-multiline", "true");
        editor.setAttribute("aria-label", editorKind === "prompt" ? "Question prompt" : "Passage text");
        editor.innerHTML = initialHtml(textarea.value);
        controls.forEach(function (control) { toolbar.appendChild(createButton(control[0], control[1], control[2], control[3], editor)); });
        shell.appendChild(toolbar);
        shell.appendChild(editor);
        textarea.hidden = true;
        textarea.parentNode.insertBefore(shell, textarea.nextSibling);
        function sync() { textarea.value = editor.innerHTML; }
        editor.addEventListener("input", sync);
        const form = textarea.closest("form");
        if (form) form.addEventListener("submit", sync);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("textarea[data-rich-text-editor]").forEach(enhance);
    });
})();
