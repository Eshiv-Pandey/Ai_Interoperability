# AP2 V11 pinned public CA metadata and safe CI diagnostics

11 November 2026. V11 is a separate prospective successor to frozen V10.
The exact 13 cases, eight arms and 104 slots remain unchanged: 65 native
policy cells and 39 repeated legal bridge prefix/initiation slots. Project
scope, source-bank IDs and checkpoint weights are unchanged.

V10 run `42905259371`, commit `74ed803d`, retained conventional smoke return
code 3 with `ValueError: non_certificate_non_comment_PEM_content`. Its actual
trace identifies `certificate_count` line 50, `prepare_public_certificates`
line 74 and worker line 721. Only the first admission-stage record was written.
The partial public copies contain the two pinned SDK certificates and the
top-level certifi bundle. The unchanged ordered helper next processes
`grpc/_cython/_credentials/roots.pem`; the failed installed file's bytes were
not retained. All 104 matrix slots remain missing, with no new original
application, native transport or provider outcome established.

The actual pip report pins grpcio 1.85.0's Linux CPython 3.13 wheel, SHA256
`55cee7cfe71b29f6b377681936f9a5f35e59f5c941a4d84e2712cb309753e7a9`.
An independently downloaded, hash-verified copy contains the exact 530,344-byte
public bundle, SHA256
`e3ada9517680b712e979331df3c34d805ebcdcbb14da13dcce004f4171e4b8ee`.
It has 99 public X.509 PEM certificates and OpenSSL public certificate text
before the PEM blocks. Its 379,861-byte non-PEM remainder has SHA256
`488a82c0e643c938b702c9fa92707d35a9a7907055e408fd87642d72afb31296`.
The pinned input reproduces V10's parser refusal. This is package-source
reconstruction; it does not pretend the failed installed file was captured.

V11 permits that public text only for the canonical declared gRPC runtime
path and those exact whole-file and remainder identities. The actor helper
and separate evaluator still require only CERTIFICATE PEM labels, reject
key material and other PEM types, and parse the X.509 certificates with
stdlib SSL. Other files keep the original certificate/comment-only rule.
The five public-file admissions remain read-only. The real bundle, original
package license and byte/provenance receipt are retained under
`benchmark/ap2-native-bridge-development-v11/public-ca-fixtures/grpcio-1.85.0`.

The new diagnostic launcher executes its supplied actor command exactly once,
captures raw stdout/stderr into separate retained launcher files, and prints
only bounded owned metadata after the process returns. It then preserves the
actor return code, including when the printer fails. Smoke execution stops on
that original nonzero code; no diagnostic retry reruns the application.
The matrix also emits safe diagnostics after preserving each actual closing
dispatch receipt. Existing interruption finalization and replay refusal remain.

CI output includes only an allowlisted failure type, validated public-code
frame file/function/line metadata, safe guard operation/code/path and loopback
endpoint metadata, known stage labels and the actual return code. Unknown
paths, function names, external host names and unexpected labels are redacted.
Error messages, source-line text, application output, argument values, locals,
headers and environment values are excluded. Inputs are limited to 256 KiB
per diagnostic file; output is limited to 32 KiB, 12 frames per row, eight
guard rows and 12 stage records. Missing, malformed or oversized files produce
fixed status labels without echoing their contents.

Thirty-six constructed owner controls passed: 24 inherited allocation,
source/guard/transport and real-helper prelude checks, six actual gRPC bundle
controls and six safe-output/isolated-launch/return-code checks. The gRPC
controls reproduce the frozen refusal, verify all 99 certificates, and reject
wrong paths, changed metadata, key/other PEM blocks and jointly altered supplied
hashes. The diagnostic controls execute only fresh generic programs, including
a single failing child whose raw streams stay out of the emitted metadata.
No original AP2 application, bridge or provider executed locally.

A copied prelude control initially still selected actor 10 instead of candidate
11. Its failed source and receipt remain retained under
`docs/research/source-evidence/ap2-v11-constructed-prelude-copy-failure-v1`.
The corrected controls select the actual candidate and use its real helpers.
This failed constructed check is separate from all hosted application evidence.

Python 3.13.1, A2A SDK 0.3.24 and Node v22.23.2 remain the hosted pins. No
private/network/process denial rule is weakened. V8's omitted network caller
remains unattributed; any future probe must be identified from actual safe
endpoint/frame records before a separate exception is considered. V11 provides
no full ADK shopper, canonical launcher, live-provider, held-out comparative,
human-gold or complete bidirectional bridge qualification. Frozen V8 through
V10 files and failures remain unchanged. Hosted V11 outcomes are pending.

Workflow: `.github/workflows/ap2-native-bridge-development-v11.yml`.
Planned artifact: `ap2-native-tcp-legal-bridge-initiation-development-v11`.
