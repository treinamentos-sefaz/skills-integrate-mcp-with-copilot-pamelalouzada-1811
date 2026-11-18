document.addEventListener("DOMContentLoaded", async () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const loginButton = document.getElementById("login-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  const closeLoginButton = document.getElementById("close-login-button");
  const teacherSession = document.getElementById("teacher-session");
  const teacherName = document.getElementById("teacher-name");
  const logoutButton = document.getElementById("logout-button");
  let isTeacher = false;

  function escapeHtml(value) {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return String(value).replace(/[&<>"']/g, (character) => replacements[character]);
  }

  function updateAuthControls(username) {
    isTeacher = Boolean(username);
    loginButton.classList.toggle("hidden", isTeacher);
    teacherSession.classList.toggle("hidden", !isTeacher);
    signupContainer.classList.toggle("hidden", !isTeacher);
    teacherName.textContent = username ? `Signed in as ${username}` : "";
  }

  async function fetchAuthStatus() {
    try {
      const response = await fetch("/auth/me");
      if (!response.ok) {
        throw new Error(`Authentication status request failed (${response.status})`);
      }
      const status = await response.json();
      updateAuthControls(status.authenticated ? status.username : null);
    } catch (error) {
      updateAuthControls(null);
      console.error("Error checking teacher session:", error);
    }
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const safeName = escapeHtml(name);
        const safeDescription = escapeHtml(details.description);
        const safeSchedule = escapeHtml(details.schedule);

        const spotsLeft =
          details.max_participants - details.participants.length;

        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => {
                      const safeEmail = escapeHtml(email);
                      const removeButton = isTeacher
                        ? `<button class="delete-btn" data-activity="${safeName}" data-email="${safeEmail}" aria-label="Remove ${safeEmail}">❌</button>`
                        : "";
                      return `<li><span class="participant-email">${safeEmail}</span>${removeButton}</li>`;
                    }
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${safeName}</h4>
          <p>${safeDescription}</p>
          <p><strong>Schedule:</strong> ${safeSchedule}</p>
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
        }
      );

      const result = await response.json();

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
        }
      );

      const result = await response.json();

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

  loginButton.addEventListener("click", () => {
    loginMessage.textContent = "";
    loginMessage.classList.add("hidden");
    loginDialog.showModal();
  });

  closeLoginButton.addEventListener("click", () => loginDialog.close());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("teacher-username").value;
    const password = document.getElementById("teacher-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in");
      }

      loginForm.reset();
      loginDialog.close();
      await fetchAuthStatus();
      await fetchActivities();
    } catch (error) {
      loginMessage.textContent = error.message || "Unable to sign in";
      loginMessage.className = "error";
      loginMessage.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error(`Sign out failed (${response.status})`);
      }
      await fetchAuthStatus();
      await fetchActivities();
    } catch (error) {
      messageDiv.textContent = "Unable to sign out. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing out:", error);
    }
  });

  // Initialize app
  await fetchAuthStatus();
  fetchActivities();
});
