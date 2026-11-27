document.querySelectorAll(".batch-form").forEach((form) => {

    const countInput = form.querySelector(
        'input[name="count"]'
    );

    const preview = form.querySelector(
        ".batch-preview"
    );

    function updatePreview() {

        const count = Number(countInput.value);

        if (
            !Number.isInteger(count) ||
            count < 1 ||
            count > 50
        ) {

            preview.textContent =
                "Введите число от 1 до 50.";

            return;
        }

        preview.textContent =
            `Будет создано ячеек: ${count}`;

    }

    countInput.addEventListener(
        "input",
        updatePreview
    );

    updatePreview();

});