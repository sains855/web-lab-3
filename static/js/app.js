function updateStatus(select) {
    const taskId = select.dataset.taskId;
    const status = select.value;

    const formData = new FormData();
    formData.append("status", status);

    fetch(`/tasks/status/${taskId}`, { method: "POST", body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                const row = select.closest("tr");
                if (row) {
                    row.style.transition = "background .3s";
                    row.style.background = "#f0fdf4";
                    setTimeout(() => { row.style.background = ""; }, 800);
                }
            }
        })
        .catch(console.error);
}
