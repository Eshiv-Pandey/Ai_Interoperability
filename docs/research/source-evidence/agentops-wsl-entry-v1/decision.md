# WSL entrypoint correction

26 October 2026. The user reported `execvpe(python3) failed: No such file or
directory` after invoking WSL without a distribution name. A read-only live
Windows registry inspection confirms two WSL2 distributions: `docker-desktop`
is the default, while `Ubuntu` is separately installed. This failure is at the
WSL process-launch boundary, before the Linux research runner. The Linux runtime,
dependency receipt and native-v4 attempt directories are still absent.

Use the new PowerShell launcher from the project directory:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_wsl_v4.ps1
```

It selects `Ubuntu` explicitly, passes the absolute project directory through
WSL `--cd`, and checks Python >=3.11, Linux x86_64, glibc and the required project
files. `-PreflightOnly` runs only these checks. Existing attempt paths stop setup.
No WSL default is changed and no operating system is installed. Successful
preflight invokes the unchanged Linux-v4 setup/control once. Its dependency
installation and offline native-test scope remain defined by the
[Linux protocol](../agentops-native-probe-v4/protocol.md).

The wrapper passed PowerShell syntax parsing and a separate AI-agent review.
These are not a Linux execution or human scientific review. The sandbox still
cannot enumerate WSL through its service, so no repeat service probe or actual
Linux preflight was attempted here. Ubuntu's Python version is unverified.
The user must run the launcher in normal PowerShell for that check.

Three context records are snapshotted under continuation-v10. The original v3
failure, Linux-v4 scripts/protocol and their 21-test validation remain unchanged.
No native/HTTP/bridge result or research-gate credit is added. CP2 remains open,
CP7 pending and verified deliverable credit remains 5%.
