# Portable retained input corpus v1

`scripts/capture_loss_benchmark_inputs_v1.py` exports exactly the files pinned by `benchmark/loss-v1/retained-manifest.json` into a fresh mirror, preserving the original relative paths and file bytes. This is an input export for retained reanalysis. It executes no archived source program, dependency, provider, model, MCP/A2A service, or experiment. It does not convert retained evidence into fresh evidence.

The mirror belongs at `benchmark/loss-v1/retained-inputs/`. Its `inventory.json` records the existing manifest's SHA-256 and byte size, the unique file count, total pinned-file bytes, and every copied path, SHA-256 and byte size. The inventory is an additional export receipt; it does not modify or replace the retained manifest. Source code, attribution and any license notices inside the pinned files are copied byte-for-byte with their original files. No extra dependency tree is collected or executed.

To create a new mirror from the original workspace inputs, use a fresh output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/capture_loss_benchmark_inputs_v1.py --root . --manifest benchmark/loss-v1/retained-manifest.json --output benchmark/loss-v1/retained-inputs
```

The exporter verifies all source paths and SHA-256 pins before allocating the destination. It caches those exact verified bytes, writes each destination with no-clobber mode, then checks the copied bytes and mirror census. An existing destination is refused, including an empty directory. Failed source hashes, missing files, duplicate JSON keys, duplicate or Windows-colliding paths, parent traversal, absolute/drive/UNC paths, symlinks/junctions in source, manifest or destination ancestors, alternate streams, invalid Windows filename characters and device names are rejected. Conventional credential/configuration files and private local instruction paths are explicitly excluded. A partial copy interrupted after allocation remains available for inspection; it is never silently reused or overwritten.

The retained normalizer can reanalyse the copied corpus with the mirror as its root and the unchanged original manifest as an independently resolved manifest path. Run from the checkout root into a new output path:

```powershell
.\.venv\Scripts\python.exe -B scripts/build_loss_benchmark_retained_v1.py --root benchmark/loss-v1/retained-inputs --manifest benchmark/loss-v1/retained-manifest.json --output runs/loss-benchmark-retained-v1/portable-reanalysis-new
```

The manifest path is resolved independently of `--root`; do not prepend the mirror root to it. Reanalysis consumes the retained bytes only and preserves their evidence kinds, missing observations, historical scope and provenance. It does not start services.

Exporter tests use tiny authored fixtures, including binary data and a test license notice. They check exact copy and inventory binding, corrupt source/hash refusal before allocation, overwrite refusal, escaping and private path rejection, missing and duplicate pins, symlink escape refusal when the operating system supports creation, and CLI roundtrip. These tests are software controls and are not historical research evidence.

The completed mirror contains **106 unique pinned files totaling 2,866,511 bytes**, plus `inventory.json`. The source manifest SHA-256 is `f346a56ae154f82c1bbcfc6ed254bfd89500f57de6e2e84a83960ae0d2e77f5a`. The exporter was executed once into the fresh `benchmark/loss-v1/retained-inputs` directory, and every destination file was checked against its original pin. That output name is now consumed; another export must choose a new output directory.

Ten exporter controls ran: nine passed, and the actual symlink-creation test was skipped because that operation was unavailable to the test process. Link and junction rejection branches were also covered without requiring privilege. Independent tiny-fixture checks successfully created Windows junctions and verified rejection of source, manifest and output ancestors before allocation, duplicate-key rejection, and exact cached copies after a deliberate source mutation following preflight. No historical service or archived source program was executed by these checks.
