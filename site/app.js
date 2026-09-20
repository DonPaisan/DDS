/* Survey renderer. Reads window.DDS_SURVEY, renders one step at a time,
 * and reports every view / completion / back / error / submit to DDS.track. */
(function () {
  var S = window.DDS_SURVEY, C = window.DDS_COMPLIANCE, CFG = window.DDS_CONFIG || {};
  if (!S || !C) return;

  var US_STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"];

  var root = document.getElementById("survey");
  var answers = {};
  var idx = 0;
  var stepShownAt = 0;
  var started = false;
  var submitting = false;

  function $(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "text") el.textContent = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k.indexOf("on") === 0) el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) el.appendChild(c); });
    return el;
  }

  function fillHero() {
    var h = S.hero || {};
    var set = function (id, txt) { var el = document.getElementById(id); if (el && txt) el.textContent = txt; };
    set("hero-eyebrow", h.eyebrow); set("hero-headline", h.headline); set("hero-subhead", h.subhead); set("hero-cta", h.cta);
    var trust = document.getElementById("hero-trust");
    if (trust && h.trust) { trust.innerHTML = ""; h.trust.forEach(function (t) { trust.appendChild($("li", { text: t })); }); }
    set("survey-reassurance", S.reassurance);
    var disc = document.getElementById("disclosures");
    if (disc) C.disclosures.forEach(function (d) { disc.appendChild($("p", { text: d })); });
    var cta = document.getElementById("hero-cta");
    if (cta) cta.addEventListener("click", function () {
      DDS.track("cta_click", { step: null, question_id: null });
      document.getElementById("survey-card").scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(function () { var f = root.querySelector("button, input, select"); if (f) f.focus({ preventScroll: true }); }, 400);
    });
    if (CFG.phoneDisplay) { var p = document.getElementById("header-phone"); if (p) { p.textContent = CFG.phoneDisplay; p.href = "tel:" + CFG.phoneDisplay.replace(/\D/g, ""); p.hidden = false; } }
  }

  function markStarted() {
    if (started) return;
    started = true;
    DDS.track("survey_start", { step: 0, question_id: S.steps[0].id });
  }

  function progress() {
    var pct = Math.round((idx / S.steps.length) * 100);
    var bar = document.getElementById("progress-bar");
    var lbl = document.getElementById("progress-label");
    if (bar) bar.style.width = Math.max(pct, 6) + "%";
    if (lbl) lbl.textContent = "Step " + (idx + 1) + " of " + S.steps.length;
  }

  function complete(step, answer, ms) {
    DDS.track("step_complete", { step: idx, question_id: step.id, answer: answer, ms: ms });
  }

  function next(step, answer) {
    var ms = Date.now() - stepShownAt;
    answers[step.id] = answer;
    complete(step, step.type === "contact" ? null : answer, ms);
    if (idx < S.steps.length - 1) { idx++; render(); }
  }

  function back() {
    if (idx === 0) return;
    DDS.track("step_back", { step: idx, question_id: S.steps[idx].id });
    idx--; render();
  }

  function render() {
    var step = S.steps[idx];
    stepShownAt = Date.now();
    DDS.setStep(idx, step.id);
    DDS.track("step_view", { step: idx, question_id: step.id });
    progress();
    root.innerHTML = "";

    var head = $("div", { class: "q-head" }, [
      $("h2", { class: "q-title", text: step.question, id: "q-title" }),
      step.help ? $("p", { class: "q-help", text: step.help }) : null
    ]);
    root.appendChild(head);

    var body = $("div", { class: "q-body", role: "group", "aria-labelledby": "q-title" });
    root.appendChild(body);

    if (step.type === "choice") {
      step.options.forEach(function (o) {
        body.appendChild($("button", { type: "button", class: "opt" + (answers[step.id] === o.value ? " selected" : ""), text: o.label,
          onclick: function () { markStarted(); next(step, o.value); } }));
      });
    } else if (step.type === "multi") {
      var sel = (answers[step.id] || []).slice();
      step.options.forEach(function (o) {
        var b = $("button", { type: "button", class: "opt multi" + (sel.indexOf(o.value) >= 0 ? " selected" : ""), text: o.label, "aria-pressed": sel.indexOf(o.value) >= 0 });
        b.addEventListener("click", function () {
          markStarted();
          var i = sel.indexOf(o.value);
          if (i >= 0) sel.splice(i, 1); else sel.push(o.value);
          b.classList.toggle("selected"); b.setAttribute("aria-pressed", i < 0);
          err.textContent = "";
        });
        body.appendChild(b);
      });
      var err = $("p", { class: "err", role: "alert" });
      body.appendChild(err);
      body.appendChild($("button", { type: "button", class: "btn primary", text: step.continueLabel || "Continue", onclick: function () {
        if (!sel.length) { err.textContent = "Please pick at least one."; DDS.track("field_error", { extra: { field: step.id, reason: "empty" } }); return; }
        next(step, sel);
      } }));
    } else if (step.type === "select") {
      var s = $("select", { class: "input", "aria-label": step.question });
      s.appendChild($("option", { value: "", text: "Choose your state…" }));
      US_STATES.forEach(function (st) { s.appendChild($("option", { value: st, text: st })); });
      if (answers[step.id]) s.value = answers[step.id];
      s.addEventListener("change", function () { if (s.value) { markStarted(); next(step, s.value); } });
      body.appendChild(s);
    } else if (step.type === "contact") {
      renderContact(step, body);
    }

    if (idx > 0) root.appendChild($("button", { type: "button", class: "btn link back", text: "← Back", onclick: back }));
    var first = body.querySelector("input, select");
    if (first && idx > 0) setTimeout(function () { first.focus({ preventScroll: true }); }, 50);
  }

  function renderContact(step, body) {
    var form = $("form", { novalidate: "novalidate", autocomplete: "on" });
    var inputs = {};
    step.fields.forEach(function (f) {
      var inp = $("input", { class: "input", type: f.type, name: f.name, id: "f-" + f.name, autocomplete: f.autocomplete || "on", inputmode: f.type === "tel" ? "tel" : f.type === "email" ? "email" : "text", required: "required" });
      inputs[f.name] = inp;
      var e = $("p", { class: "err", id: "e-" + f.name, role: "alert" });
      inp.addEventListener("focus", function () { markStarted(); DDS.track("field_focus", { extra: { field: f.name } }); });
      inp.addEventListener("input", function () { e.textContent = ""; });
      form.appendChild($("label", { class: "field" }, [$("span", { text: f.label }), inp, e]));
    });

    var consent = $("input", { type: "checkbox", id: "consent", required: "required" });
    var consentErr = $("p", { class: "err", id: "e-consent", role: "alert" });
    form.appendChild($("label", { class: "consent" }, [consent, $("span", { text: C.consentLabel })]));
    form.appendChild(consentErr);

    var submitBtn = $("button", { type: "submit", class: "btn primary big", text: step.submitLabel || "Submit" });
    form.appendChild(submitBtn);
    form.appendChild($("p", { class: "note", text: C.submitNote }));
    form.appendChild($("p", { class: "note" }, [$("a", { href: C.privacyPolicyPath, text: "Privacy Policy", target: "_blank", rel: "noopener" })]));
    var formErr = $("p", { class: "err", role: "alert" });
    form.appendChild(formErr);

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (submitting) return;
      var errors = validate(inputs, consent.checked);
      Object.keys(inputs).forEach(function (k) { document.getElementById("e-" + k).textContent = errors[k] || ""; });
      consentErr.textContent = errors.consent || "";
      var keys = Object.keys(errors);
      if (keys.length) {
        keys.forEach(function (k) { DDS.track("field_error", { extra: { field: k, reason: errors[k] } }); });
        var firstBad = inputs[keys[0]] || consent; firstBad.focus();
        return;
      }
      submitting = true;
      submitBtn.disabled = true; submitBtn.textContent = "Sending…";
      var contact = { first_name: inputs.first_name.value.trim(), phone: inputs.phone.value.replace(/\D/g, ""), email: inputs.email.value.trim().toLowerCase() };
      var ms = Date.now() - stepShownAt;
      complete(step, null, ms);
      var eventId = DDS.track("form_submit", { step: idx, question_id: step.id });
      var payload = {
        event_id: eventId,
        session_id: DDS.sessionId,
        visitor_id: DDS.visitorId,
        survey_version: S.version,
        consent_version: C.version,
        consent_text: C.consentLabel,
        answers: answers,
        contact: contact,
        attr: DDS.attr,
        page_url: location.href,
        fbp: (document.cookie.match(/(?:^|; )_fbp=([^;]*)/) || [])[1] || null,
        fbc: (document.cookie.match(/(?:^|; )_fbc=([^;]*)/) || [])[1] || null
      };
      fetch(CFG.leadEndpoint || "/api/lead", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then(function (r) { return r.ok ? r.json() : r.json().then(function (j) { throw new Error(j.error || ("HTTP " + r.status)); }); })
        .then(function (j) {
          DDS.track("lead", { step: idx, question_id: step.id, extra: { lead_id: j.lead_id || null } });
          try { sessionStorage.setItem("dds_lead", JSON.stringify({ lead_id: j.lead_id, first_name: contact.first_name })); } catch (e) {}
          setTimeout(function () { location.href = "/thank-you.html"; }, 250);
        })
        .catch(function (e) {
          submitting = false; submitBtn.disabled = false; submitBtn.textContent = step.submitLabel || "Submit";
          formErr.textContent = "Something went wrong sending your info. Please try again" + (CFG.phoneDisplay ? " or call " + CFG.phoneDisplay : "") + ".";
          DDS.track("lead_error", { extra: { message: String(e.message).slice(0, 200) } });
        });
    });
    body.appendChild(form);
  }

  function validate(inputs, consented) {
    var errors = {};
    if (!inputs.first_name.value.trim()) errors.first_name = "Please enter your first name.";
    var digits = inputs.phone.value.replace(/\D/g, "");
    if (digits.length === 11 && digits[0] === "1") digits = digits.slice(1);
    if (digits.length !== 10) errors.phone = "Please enter a 10-digit phone number.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(inputs.email.value.trim())) errors.email = "Please enter a valid email.";
    if (!consented) errors.consent = "Please check the box so we're allowed to contact you.";
    return errors;
  }

  fillHero();
  render();
})();
