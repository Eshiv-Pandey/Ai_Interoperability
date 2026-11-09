# AgentOps Linux filesystem attempt v5

26 October 2026. Prospective environment correction and evidence-export protocol.

The prior explicit-Ubuntu launch reached locked installation. Its retained
`dependencies-linux-v4/result.json` reports failure, and `locked-sync.stderr.bin`
identifies permission denial while uv renamed a temporary cache directory under
`/mnt/p` into its archive cache. No native test or HTTP request ran. Its runtime,
cache, receipts and original source remain unchanged. A direct sandbox Ubuntu
probe still returned `Wsl/Service/E_ACCESSDENIED`; executing the next command
requires normal user PowerShell.

## New environment and unchanged controls

The v5 wrapper makes one exclusive attempt under
`runs/agentops-native-eligibility/linux-filesystem-v5`. It requires glibc Linux
x86_64, identifies `/tmp`'s backing mount through `/proc/self/mountinfo`, and
accepts only ext4/xfs/btrfs/overlay. Windows-backed, network and memory-backed
mounts are excluded. It creates one fresh Linux temporary workspace and checks
mode-0700 write, directory rename, symlink read and native fcntl locking before
installation. The Linux directory is preserved on success or failure.

Only the exact 421 original regular source files, the original ingestion
manifest and an explicit harness/protocol dependency list are copied. Every
input is hashed before copying and checked afterward. Original source and v4
controller bytes are unchanged. All relative paths retain their original
meaning inside the replica; its absolute Linux root is explicitly recorded.
An inaccessible, changed or missing input stops the attempt.

The unchanged Linux-v4 setup/controller runs in the replica, which has no prior
attempt directories. Its existing once-only native and effect checks apply.
This is a separately named environment attempt, not a rerun or overwrite of the
parent v4 installation failure. No native success is presumed. On success only,
HTTP-v2 is prepared against the actual native result/runtime and then run once.
Its five original-factory HTTP exchanges and separate semantic/effect checks
remain governed by the [HTTP-v2 protocol](../agentops-http-control-v2/protocol.md).
Native failure stops before HTTP preparation. Any failure is retained.

## Evidence and limits

Bootstrap stdout/stderr and child-process launch/completion receipts are written
to the parent project. Each stage has a finite timeout. Setup children have
their own existing process-group cleanup; the outer wrapper also stops its
owned child group on timeout/interruption. No claim is made that an abrupt OS
termination produces a final receipt or cleans every independently detached
descendant. Such an interrupted workspace must be inspected before a new attempt.

At terminal outcome the exporter copies exact inputs, regular run files and
explicitly referenced runtime metadata/selected source bytes into an independent
`workspace` subtree of the v5 output. Pytest convenience symlinks are retained as
inert path/target manifest entries, never followed or materialized. Hashed file
references through symlinks, path traversal, conflicting hashes and missing
referenced bytes are rejected; it caps export at 512 MiB and
retains the Linux original if export fails. Embedded Linux paths and direct-URL
metadata are not rewritten. Relative paths in exported receipts resolve against
this exported replica root, never the parent failed-v4 namespace. Absolute
paths identify the original Linux execution location. This is an evidence
package, not a complete executable copy of installed dependencies.

When runtime inspection exists, the export additionally retains the installed
ADK A2A and SDK compatibility Python sources for the next confirmation-channel
analysis. These are labeled post-execution snapshots, not retroactive proof
that every such file was authenticated before execution. Their absence or a
typed-versus-raw distinction cannot itself demonstrate algorithmic novelty.

The package records actual outcomes separately from export integrity. No
installation, software test or successful control adds scientific gate credit.
Native/HTTP validity does not establish bridge qualification, second-domain
human validity, C1 novelty, full evaluation, reproduction or human review.

Run once from normal PowerShell in the project directory:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v5.ps1
```

This downloads the original locked dependencies into the new Linux workspace,
runs the offline native control and, only if it passes, local HTTP controls.
It changes no WSL default, source/seed, mount configuration, permissions of old
artifacts, system packages, cloud resource or live-model configuration.
