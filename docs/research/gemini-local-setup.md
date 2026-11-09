# Configure a Gemini API key locally on Windows

Keep the key out of chat. In the project folder, double-click
[Configure Gemini.cmd](../../Configure%20Gemini.cmd). Paste the key into the
masked field with **Ctrl+V**, then choose **Save**. Cancel closes the dialog
without replacing a saved key. Opening the dialog never displays an existing key.

Use a key from the Google AI Studio project whose Gemini API access you intend
to use. If you intend to use the free tier, confirm that project's tier and
billing settings in Google AI Studio. These helpers do not enforce free-tier
billing or check a key with Google. Setup makes no API calls and installs nothing.

The key is stored as Windows DPAPI ciphertext at:

```text
%LOCALAPPDATA%\AiInteroperability\credentials\gemini-api-key.dpapi
```

It is encrypted for the current Windows user on this computer. It is outside
the project, source captures and run records; no plaintext `.env` file or
persistent environment variable is created. Save replaces the ciphertext
atomically in the same folder. To replace a key later, reopen the dialog and
save the new value. Copying this file to a different Windows account is not a
supported way to transfer the key.

From PowerShell in the project folder, check whether a saved key can be opened
locally without displaying it:

```powershell
powershell.exe -NoProfile -File scripts/configure_gemini_key.ps1 -CheckOnly
```

The output contains only `configured` and the storage `path`. `configured: true`
means the local protected value is readable by this account; it does not verify
provider acceptance, quotas or billing. The launcher uses the existing Windows
PowerShell execution policy and does not change it.

To give a local Python program access to the saved key for one invocation:

```powershell
& .\scripts\with_gemini_key.ps1 -Program python -ProgramArguments @('-B', 'path\to\your_gemini_program.py')
```

Replace the example program path with the intended program. The launcher accepts
an executable and its arguments, decrypts the key locally, and supplies
`GOOGLE_API_KEY` and `GEMINI_API_KEY` to that child, as documented in
[Google's API-key guide](https://ai.google.dev/gemini-api/docs/api-key). It sets
`GOOGLE_GENAI_USE_VERTEXAI=false` for the same invocation. All previous values
in the launcher's environment are restored afterward, including when the child
fails, and its exit code is forwarded. The helper clears its unmanaged secret
buffer and disposes its secure-string object. The child program can make API
calls and incur usage according to its own behavior and the configured project.

This launcher is for a native Windows program. It does not arrange credential
forwarding into WSL, Docker or another machine.

The [existing algorithm/benchmark rehearsal](shared-admission-command-v1.md)
uses authored finite models and needs no Gemini key. Saving this key alone does
not connect a Gemini model to that benchmark or establish live admission success.

## Verified metadata access: 29 October 2026

The masked entry window closed successfully, and a fresh local check returned
`configured: true`. The separate [metadata checker](../../scripts/check_gemini_model_access_v1.py)
then made one authenticated GET for the unchanged AP2 router's exact model,
`gemini-3.1-flash-lite-preview`. The [retained receipt](../../runs/gemini-access/metadata-v1/result.json)
records HTTP 200, matching model identity and advertised `generateContent`.
No content generation, AP2 execution or billing change occurred.

The checker uses a fixed HTTPS endpoint, verified TLS, a 20-second timeout,
no redirects or retries, and a key supplied only in the request header. It
retains sanitized status and boolean metadata; it does not save provider bodies,
headers, keys or exception text. It refuses an existing output directory.
The consumed `metadata-v1` allocation must be preserved. Its invocation was:

```powershell
& .\scripts\with_gemini_key.ps1 -Program C:\Python313\python.exe -ProgramArguments @('-B', 'scripts/check_gemini_model_access_v1.py', '--output', 'runs/gemini-access/metadata-v1')
```

This metadata result does not establish generation quota, the project's
free-tier/billing settings or native AP2 admission. See Google's [model metadata reference](https://ai.google.dev/api/models).

## Verified synthetic tool routing: 29 October 2026

The separate [bounded tool checker](../../scripts/check_gemini_tool_access_v1.py)
made one generation request using the same model and forced function mode `ANY`,
with a 32-output-token limit. [The retained tool-smoke-v1 receipt](../../runs/gemini-access/tool-smoke-v1/result.json)
records HTTP 200 and one `acknowledge_connectivity` call with empty arguments.
Reported usage was 45 prompt tokens and 10 output tokens, 55 total.

The request is a synthetic connectivity check. No returned function or original
AP2 code was executed. The unchanged AP2 router's declaration-only tool shape
and forced mode motivated the request; the synthetic function and output cap
are explicit test configuration. No generated text, thought signatures, provider
body, credential or exception text is retained. The checker uses the same fixed
HTTPS/verified-TLS/no-redirect/no-retry approach as the metadata check and
preserves its single attempted request on failures.

Its consumed invocation was:

```powershell
& .\scripts\with_gemini_key.ps1 -Program C:\Python313\python.exe -ProgramArguments @('-B', 'scripts/check_gemini_tool_access_v1.py', '--output', 'runs/gemini-access/tool-smoke-v1')
```

Preserve `tool-smoke-v1`; do not repeat it to seek a favorable result. A successful
single request does not guarantee future quota or identify the project's billing
tier. Native AP2 execution and original-task/effect qualification remain open.
