# AP2 report-derived wheel artifact locks v1

30 October 2026. The
[reviewed exporter](../../scripts/export_ap2_wheel_lock_v1.py) completed two
exclusive report-only exports. It did not repeat either resolver, fetch a wheel,
build, install or import acquired source. Exact report/result/plan and captured
source-input bytes are retained in each allocation; each export's nine read
inputs remained unchanged.

| Artifact selection | Distributions | Frozen manifest | Hash-pinned URL requirements |
| --- | ---: | --- | --- |
| Indexed runtime | 184 | [indexed-wheel-lock-v1](../../runs/ap2-dependency-resolution/indexed-wheel-lock-v1/manifest.json) | [Runtime wheel URLs](../../runs/ap2-dependency-resolution/indexed-wheel-lock-v1/wheel-url-requirements.txt) |
| Declared build backends | 7 | [build-backend-wheel-lock-v1](../../runs/ap2-dependency-resolution/build-backend-wheel-lock-v1/manifest.json) | [Backend wheel URLs](../../runs/ap2-dependency-resolution/build-backend-wheel-lock-v1/wheel-url-requirements.txt) |

Both manifests use schema `ap2-report-derived-wheel-artifact-lock/1` and status
`frozen_report_derived_indexed_artifacts`. Every wheel row retains exact
name/version, public wheel URL, filename, report SHA256, complete metadata and
download-info object. Selected URLs are HTTPS `files.pythonhosted.org` wheels;
decoded filenames contain no separators/whitespace; names are unique within
each selection and none shadows local `ap2`, `ap2-samples` or `x402-a2a`.
Unexpected yanked/unclassified artifacts are rejected.

The recorded command must begin with the original native interpreter followed
by `-I -m pip --isolated install`, and include the actual binary-only dry-run,
explicit public PyPI target, no-input/no-cache/version-check controls and child
`PIP_CONFIG_FILE=nul`. These guards were reviewed and corrected before the first
exports. Source selection and input-v1 stayed unchanged.

The wheel hashes remain report-derived until actual fetched wheel bytes are
checked. `wheel_bytes_independently_verified`, downloads by export, builds,
installation, original-source imports, native execution and complete combined
environment remain false. The seven declared backend artifacts select
setuptools `84.2.1` and Hatchling `1.33.0` plus reported transitive tools; dynamic
backend-hook requirements are still unverified. Keep these backend inputs
separate from runtime selection rather than claiming one ready environment.

## Source staging map and next step

Focused static comparison found no missing retained file among all 134 original
AP2 Python SDK/sample subtree files and root pyproject/README/LICENSE. The SDK
package namespace is `ap2` under `code/sdk/python`; sample roots are `common`
and `roles` under `code/samples/python/src`. All three HP role `agent.json`
assets are present and must remain beside the original modules. Wheel resource
inclusion is unverified because the original pyprojects do not explicitly list
those JSON resources. Inspect built wheels and execute originals from their
bound source layout without editing upstream packaging.

The original full tree also identifies two assets outside the captured Python
subtrees: `code/samples/certs/issuer_cert_sdjwt.pem` and `ds_cert_sdjwt.pem`.
Their blob IDs are respectively `dd1e7ba01972cf3ca5c566e4572294606d2992b4` and
`b2b717529196fc44f1191b1aeedec64822505b3d`, sizes 1005/1066 bytes. Merchant and
credentials-provider source locate them relative to `code/samples`. The
[original retained tree](source-evidence/ap2-procurement-screen-v1/tree-response.json)
is nontruncated and matches the AP2 pin's tree
`948843cae3e6423e744a556fe0967bf395aa2ac5`; no different source is needed to
acquire them. Root's new certificate/staging work remains separately recorded.

The next concrete step is one frozen wheel acquisition that verifies actual
bytes against these exact URL/hash manifests. Preserve failures and both
terminal resolver/export allocations. Then build the three source-bound local
wheels in separate pristine-source copies using frozen backends, retain dynamic
hook/build requirements, inspect wheel metadata/resources and install only
verified frozen artifacts into a new isolated environment. Original-source
bootstrap/native qualification remains a subsequent requirement with unchanged
resource and workflow gates. These artifact locks award no domain, full-task,
novelty or checkpoint credit.

Exporter SHA256:
`813e9b13b8781f82f246aa5078a47f42181ab92b4ed5fe3fa543db09992ded22`.
Runtime manifest/requirements SHA256:
`d1ed29b81ae3dfd6bc4d89d95d2130e88c0e287a320c77032cbf80888abde106` /
`387d91d3a87ffa72bc7134d110613b56090ba583d1055080f518372007aafdad`.
Backend manifest/requirements SHA256:
`d304cf5a3c8671bccd52fa3c4d5a7b357792aa25c5973a2ae8c2f24946da4078` /
`4f7cc78657e5fc23c97c65686a7e50e21a1a04a87e863559abe875c276a46e6e`.
