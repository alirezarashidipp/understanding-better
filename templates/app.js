function connectSkipCheckboxes() {
  for (const checkbox of document.querySelectorAll('input[name^="skip_"]')) {
    const index = checkbox.name.replace("skip_", "");
    const answer = document.getElementById("answer_" + index);
    if (!answer) {
      continue;
    }

    function updateAnswer() {
      if (checkbox.checked) {
        answer.value = "";
      }
      answer.disabled = checkbox.checked;
    }

    checkbox.addEventListener("change", updateAnswer);
    updateAnswer();
  }
}

function preventDuplicateSubmissions() {
  let submitting = false;
  const overlay = document.getElementById("loading-overlay");

  for (const form of document.querySelectorAll("form")) {
    form.addEventListener("submit", (event) => {
      if (submitting) {
        event.preventDefault();
        return;
      }

      submitting = true;
      form.setAttribute("aria-busy", "true");

      for (const button of form.querySelectorAll('button[type="submit"]')) {
        button.disabled = true;
        button.textContent = "Processing…";
      }

      if (overlay) {
        overlay.hidden = false;
      }
    });
  }
}

connectSkipCheckboxes();
preventDuplicateSubmissions();
