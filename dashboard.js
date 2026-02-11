// Sidebar toggle
const menuBtn = document.getElementById("menuBtn");
const overlay = document.getElementById("overlay");

function toggleSidebar() {
  document.body.classList.toggle("sidebar-open");
}

menuBtn?.addEventListener("click", toggleSidebar);
overlay?.addEventListener("click", () => document.body.classList.remove("sidebar-open"));

// Review status update buttons
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".btn");
  if (!btn) return;

  const id = btn.dataset.id;
  const status = btn.dataset.status;

  try {
    const res = await fetch("/update-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: Number(id), status })
    });

    const data = await res.json();
    if (data.success) {
      const statusEl = document.getElementById(`status-${id}`);
      if (statusEl) statusEl.textContent = status;
    } else {
      alert("Update failed (server said no).");
    }
  } catch (err) {
    console.error(err);
    alert("Update failed (network/server issue).");
  }
});
