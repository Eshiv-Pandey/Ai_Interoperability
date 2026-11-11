# Gemini access setup for later provider validation

On 11 November 2026 the user confirmed adding `GOOGLE_API_KEY`. A read-only
GitHub metadata check verified that secret name and its update time,
`2026-11-11T05:50:04Z`; the value was not read. Earlier retained experiments use
disclosed offline model fixtures. Their observations remain unchanged. Secret
metadata alone does not establish authentication, model access or quota.

To make the offered Gemini API key available without putting it in chat or Git:

1. Open https://github.com/Eshiv-Pandey/Ai_Interoperability/settings/secrets/actions.
2. Choose **New repository secret**.
3. Set the name to `GOOGLE_API_KEY` and put the key in the secret value field.
4. Save it. Keep the key out of source files, review files and chat messages.

The key can be obtained from https://aistudio.google.com/api-keys. Before a
provider experiment, the runner still needs a frozen model identifier,
verified current RPM/TPM/RPD and remaining access, a bounded request/usage
ledger, and the source-bound route and task checks. This setup authorizes no
purchase, quota increase or billing change. A provider run will be a separate
prospective allocation; offline observations stay labelled as offline.

Without a configured key, the scripted zero-token study and its qualification
work can continue. No paid inference or submission is required to run that core.
