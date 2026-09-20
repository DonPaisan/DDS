// ─────────────────────────────────────────────────────────────────────────────
// LOCKED COPY. Do not edit without a compliance review.
// Automated agents (see CLAUDE.md) must never modify this file.
// Everything here is legal/consent language. Survey wording lives in
// survey.config.js instead.
// ─────────────────────────────────────────────────────────────────────────────
window.DDS_COMPLIANCE = {
  version: "2026-09-20.1",

  // Shown next to the consent checkbox on the contact step. TCPA-style consent.
  consentLabel:
    "By checking this box and submitting, I agree to be contacted by Debt Direct Solutions " +
    "at the phone number and email provided, including by autodialed or prerecorded calls and " +
    "text messages, about debt relief options. Consent is not a condition of purchase. " +
    "Message and data rates may apply. Reply STOP to opt out.",

  // Shown under the submit button.
  submitNote:
    "Free, no-obligation review. Your information is kept private and is never sold.",

  // Footer disclosures. Each string becomes its own paragraph.
  disclosures: [
    "Debt Direct Solutions is a debt settlement referral service. We are not a lender, a law firm, " +
    "or a credit repair organization, and we do not provide legal, tax, or credit advice.",
    "Debt settlement programs are not available in all states. Results vary and depend on your " +
    "creditors, the amount you enroll, and your ability to save. No specific outcome, savings " +
    "percentage, or timeline is guaranteed.",
    "Enrolling in a debt settlement program may negatively affect your credit, and creditors may " +
    "continue collection activity, including possible lawsuits, until an account is settled. " +
    "Forgiven debt may be treated as taxable income.",
    "We do not assume your debts, make monthly payments to your creditors, or provide tax, " +
    "bankruptcy, or legal advice."
  ],

  privacyPolicyPath: "/privacy.html"
};
