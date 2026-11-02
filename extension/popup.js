// Client tier: sends the posting details to the backend and shows the trust score.
const API = "http://127.0.0.1:8000";
const $ = (id) => document.getElementById(id);
let pageUrl = "";

const VERDICT = {
  Green: "Low risk",
  Yellow: "Moderate risk, verify before applying",
  Red: "High risk, do not share documents or pay",
};

// Remember what was typed, so it is not lost when the popup closes.
const FIELDS = ["company", "website", "email", "text"];
FIELDS.forEach((id) =>
  $(id).addEventListener("input", () => chrome.storage.local.set({ [id]: $(id).value }))
);
chrome.storage.local.get(FIELDS).then((saved) =>
  FIELDS.forEach((id) => { if (saved[id]) $(id).value = saved[id]; })
);

chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
  pageUrl = tab?.url || "";
});

function say(text) { $("msg").textContent = text; }

$("grab").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection().toString(),
    });
    if (result) {
      $("text").value = result;
      chrome.storage.local.set({ text: result });   // setting .value in code does not fire "input"
      say("Selected text added.");
    } else {
      say("Select the job description on the page first, then try again.");
    }
  } catch (e) {
    say("This page does not allow reading its text. Paste the description instead.");
  }
});

$("check").addEventListener("click", async () => {
  const btn = $("check");
  btn.disabled = true;
  say("Checking...");
  try {
    const res = await fetch(`${API}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: $("company").value,
        company_website: $("website").value,
        recruiter_email: $("email").value,
        description: $("text").value,
        url: pageUrl,
      }),
    });
    if (!res.ok) throw new Error("Server returned " + res.status);
    show(await res.json());
    say("");
  } catch (e) {
    say("Could not reach the backend. Start it with: uvicorn app:app --reload");
  } finally {
    btn.disabled = false;
  }
});

function show(r) {
  $("result").style.display = "block";
  $("banner").className = r.label;
  $("score").textContent = r.trust_score;
  $("verdict").textContent = `${r.label}: ${VERDICT[r.label]}`;
  const ul = $("reasons");
  ul.replaceChildren();
  const items = [...r.reasons];
  if (r.community_reports) items.unshift(`${r.community_reports} community report(s) on this posting`);
  items.forEach((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  });
}

$("report").addEventListener("click", async () => {
  try {
    await fetch(`${API}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: pageUrl,
        company_name: $("company").value,
        reason: "Reported from extension",
      }),
    });
    say("Report saved. Thank you.");
  } catch (e) {
    say("Could not save the report. Is the backend running?");
  }
});

$("clear").addEventListener("click", () => {
  FIELDS.forEach((id) => { $(id).value = ""; });
  chrome.storage.local.clear();
  $("result").style.display = "none";
  say("Cleared.");
});