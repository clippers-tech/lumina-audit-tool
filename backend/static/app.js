// API base URL — routes through port-forwarded backend
const API = "";

// Form submission handler
document.getElementById("audit-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  // Clear previous errors
  hideError();

  // Gather form data
  const data = {
    full_name:       getValue("full_name"),
    email:           getValue("email"),
    company_name:    getValue("company_name"),
    industry:        getValue("industry"),
    linkedin_url:    getValue("linkedin_url")  || null,
    twitter_url:     getValue("twitter_url")   || null,
    tiktok_url:      getValue("tiktok_url")    || null,
    youtube_url:     getValue("youtube_url")   || null,
    instagram_url:   getValue("instagram_url") || null,
    own_revenue:     getValue("own_revenue")    || null,
    competitor_name: getValue("competitor_name") || null,
  };

  // Validate required fields
  if (!data.full_name || !data.email || !data.company_name || !data.industry) {
    showError("Please fill in all required fields.");
    return;
  }

  // Basic email format check
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRe.test(data.email)) {
    showError("Please enter a valid email address.");
    return;
  }

  // Validate at least one profile URL
  const urls = [
    data.linkedin_url,
    data.twitter_url,
    data.tiktok_url,
    data.youtube_url,
    data.instagram_url,
  ];
  if (!urls.some((u) => u && u.trim())) {
    showError("Please provide at least one profile URL (LinkedIn, Twitter, TikTok, YouTube, or Instagram).");
    return;
  }

  // Show loading state
  const btn = document.getElementById("submit-btn");
  btn.classList.add("loading");
  btn.disabled = true;

  // Send the audit request using keepalive fetch so it survives page navigation.
  // Also use sendBeacon as a fallback — belt and suspenders.
  const payload = JSON.stringify(data);
  const endpoint = `${API}/api/audit`;

  // Primary: fetch with keepalive (survives navigation, supports headers)
  try {
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  } catch (_) {
    // Fallback: sendBeacon (always survives navigation but limited to ~64KB)
    try {
      const blob = new Blob([payload], { type: "application/json" });
      navigator.sendBeacon(endpoint, blob);
    } catch (_) {}
  }

  // Fire Meta Pixel Lead event for ad conversion tracking
  if (typeof fbq === "function") {
    fbq("track", "Lead", {
      content_name: data.company_name,
      content_category: data.industry,
    });
  }

  // Brief pause to let the request + pixel event leave the browser
  await new Promise((r) => setTimeout(r, 500));

  // Redirect to the confirm/book page
  const params = new URLSearchParams({ email: data.email });
  window.location.href = `confirm.html?${params.toString()}`;
});

function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function showError(msg) {
  const el = document.getElementById("form-error");
  el.textContent = msg;
  el.style.display = "block";
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}

function hideError() {
  const el = document.getElementById("form-error");
  if (el) el.style.display = "none";
}
