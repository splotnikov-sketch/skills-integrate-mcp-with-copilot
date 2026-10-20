document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let accessToken = null;

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  function setAccount(token, username = "") {
    accessToken = token;
    signupForm.classList.toggle("hidden", !token);
    document.getElementById("login-notice").classList.toggle("hidden", !!token);
    document.getElementById("login-button").classList.toggle("hidden", !!token);
    document.getElementById("logout-button").classList.toggle("hidden", !token);
    document.getElementById("account-status").textContent =
      token ? `Teacher: ${username}` : "Student view";
    document.querySelectorAll(".delete-btn").forEach((button) => {
      button.classList.toggle("hidden", !token);
    });
  }

  function handleAuthFailure(response) {
    if (response.status === 401) {
      setAccount(null);
    }
  }

  document.getElementById("account-button").addEventListener("click", (event) => {
    const panel = document.getElementById("account-panel");
    panel.classList.toggle("hidden");
    event.currentTarget.setAttribute("aria-expanded", String(!panel.classList.contains("hidden")));
  });
  document.getElementById("login-button").addEventListener("click", () => {
    loginError.textContent = "";
    loginDialog.showModal();
  });
  document.getElementById("cancel-login").addEventListener("click", () => loginDialog.close());
  loginDialog.addEventListener("close", () => loginForm.reset());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("username").value;
    const submit = loginForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    loginError.textContent = "";
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password: document.getElementById("password").value }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = typeof result.detail === "string" ? result.detail : "Login failed. Check your credentials.";
        return;
      }
      setAccount(result.access_token, username);
      loginDialog.close();
    } catch (error) {
      loginError.textContent = "Unable to log in. Please try again.";
      console.error("Error logging in:", error);
    } finally {
      document.getElementById("password").value = "";
      submit.disabled = false;
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok && response.status !== 401) {
        throw new Error("Server could not revoke the session");
      }
      setAccount(null);
      messageDiv.textContent = "Logged out.";
      messageDiv.className = "success";
    } catch (error) {
      messageDiv.textContent = "Logout failed. Please try again.";
      messageDiv.className = "error";
      console.error("Error logging out:", error);
    }
  });

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Unable to load activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${escapeHTML(email)}</span><button class="delete-btn ${accessToken ? "" : "hidden"}" aria-label="Unregister ${escapeHTML(email)}" data-activity="${escapeHTML(name)}" data-email="${escapeHTML(email)}">❌</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${escapeHTML(name)}</h4>
          <p>${escapeHTML(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHTML(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();
      handleAuthFailure(response);

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();
      handleAuthFailure(response);

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  fetchActivities();
});
