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
