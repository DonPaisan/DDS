// ─────────────────────────────────────────────────────────────────────────────
// SURVEY DEFINITION. This file is the one the optimization loop is allowed to
// edit: question wording, order, answer options, help text, and step count.
//
// Rules (also in CLAUDE.md):
//   • Keep every `id` stable. Analytics are keyed by id; renaming breaks history.
//   • Bump `version` on every change so drop-off can be compared across versions.
//   • The `contact` step must stay last and must keep first_name, phone, email.
//   • Never add a field that collects PII outside the contact step.
// ─────────────────────────────────────────────────────────────────────────────
window.DDS_SURVEY = {
  version: "2026-09-20.1",

  hero: {
    eyebrow: "Free debt review",
    headline: "Struggling with credit card or medical debt?",
    subhead:
      "Answer 4 quick questions to see if you qualify to lower what you owe. " +
      "Takes about 60 seconds. No obligation.",
    cta: "See if I qualify",
    trust: ["No upfront fees", "No obligation", "Not a lender"]
  },

  steps: [
    {
      id: "debt_amount",
      type: "choice",
      question: "About how much unsecured debt do you have?",
      help: "Credit cards, medical bills, personal loans, collections. Not your mortgage or car loan.",
      options: [
        { value: "under_10k", label: "Less than $10,000" },
        { value: "10k_25k",   label: "$10,000 – $25,000" },
        { value: "25k_50k",   label: "$25,000 – $50,000" },
        { value: "over_50k",  label: "More than $50,000" }
      ]
    },
    {
      id: "debt_type",
      type: "multi",
      question: "What kind of debt is it?",
      help: "Select all that apply.",
      options: [
        { value: "credit_cards",   label: "Credit cards" },
        { value: "medical",        label: "Medical bills" },
        { value: "personal_loans", label: "Personal loans" },
        { value: "collections",    label: "Collections" },
        { value: "other",          label: "Something else" }
      ],
      continueLabel: "Continue"
    },
    {
      id: "payment_status",
      type: "choice",
      question: "Are you able to keep up with the minimum payments?",
      options: [
        { value: "on_time",     label: "Yes, but it's getting hard" },
        { value: "behind_1_2",  label: "I'm 1–2 months behind" },
        { value: "behind_3plus", label: "I'm 3 or more months behind" },
        { value: "unsure",      label: "I'm not sure" }
      ]
    },
    {
      id: "state",
      type: "select",
      question: "Which state do you live in?",
      help: "Programs vary by state, so we check this first."
    },
    {
      id: "contact",
      type: "contact",
      question: "Good news — you may qualify.",
      help: "Where should we send your free savings estimate? A specialist will reach out, usually within one business day.",
      fields: [
        { name: "first_name", label: "First name", type: "text", autocomplete: "given-name" },
        { name: "phone",      label: "Mobile phone", type: "tel", autocomplete: "tel" },
        { name: "email",      label: "Email", type: "email", autocomplete: "email" }
      ],
      submitLabel: "Get my free estimate"
    }
  ],

  // Reassurance shown below the survey card.
  reassurance: "Your answers are private and only used to match you with the right option."
};
