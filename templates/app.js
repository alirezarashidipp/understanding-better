const skipCheckboxes = document.querySelectorAll('input[name^="skip_"]');

for (const checkbox of skipCheckboxes) {
  const questionId = checkbox.name.replace("skip_", "");
  const answerInput = document.getElementById(`answer_${questionId}`);

  if (!answerInput) {
    continue;
  }

  const updateAnswerInput = () => {
    if (checkbox.checked) {
      answerInput.value = "";
    }
    answerInput.disabled = checkbox.checked;
  };

  checkbox.addEventListener("change", updateAnswerInput);
  updateAnswerInput();
}

const forms = document.querySelectorAll("form");
const loadingOverlay = document.getElementById("loading-overlay");
let isSubmitting = false;

for (const form of forms) {
  form.addEventListener("submit", (event) => {
    if (isSubmitting) {
      event.preventDefault();
      return;
    }

    isSubmitting = true;
    form.setAttribute("aria-busy", "true");
    document.body.classList.add("is-loading");

    for (const button of form.querySelectorAll('button[type="submit"]')) {
      button.disabled = true;
      button.textContent = "Processing…";
    }

    if (loadingOverlay) {
      loadingOverlay.hidden = false;
    }
  });
}
