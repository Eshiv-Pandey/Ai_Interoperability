# Independent AP2 native shopper V3 launcher review

No source blocker found in the additive V3 launcher. This review checks source and local constructed controls only; Linux and actual runtime validation remain pending.

The complete V2 to V3 diff contains fresh profile/schema/case/successor identifiers and temporary-directory/source membership, two explicit provenance flags, and the actual CLI change from `args.python.resolve()` to `args.python.absolute()`. Public actor grammar, original sources/models, limits, 120-second sender and bounded drain behavior remain inherited. The worker hash stays `f7c0e3d79582e9bfbc49123fe7fd16791c3651f9c58dab7b70a69658a548b765`.

The corrected path matches V1. `portable_runtime` and service/shopper subprocesses use the exact supplied Python path. Runtime version and `sys.prefix`/site-packages checks still precede provider smoke and original application launch. This change preserves a virtual-environment launcher symlink instead of replacing it with its global target.

Independent local verification discovered four V3 tests: three passed and the real-symlink test skipped because Windows symlink creation raised `OSError`. The test may skip only on Windows. Linux symlink failure raises; the hosted workflow runs the suite before its sole live execute step. The mocked actual CLI test proves the chosen path; it does not prove Linux runtime execution.

Source hashes and exact validation scope are in the JSON. No original SDK, application or provider was executed and no workflow was dispatched by this reviewer. Historical failures stay separate; task success, human gold and scientific qualification remain unclaimed.
