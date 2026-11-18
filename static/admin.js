document.querySelectorAll('[data-confirm-delete]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!window.confirm('確定要刪除這篇文章？')) event.preventDefault();
  });
});
