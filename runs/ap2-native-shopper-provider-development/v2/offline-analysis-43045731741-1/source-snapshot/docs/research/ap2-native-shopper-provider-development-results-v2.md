# Original native AP2 shopper: retained development observation V2

Run [43045731741](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43045731741) failed runtime preflight before provider smoke, original applications or native services. Its single allocated development task remains unexecuted. The failure supplies concrete launcher/preflight evidence; shopping behavior, 120-second sender behavior and drain behavior were unreached.

The frozen head is `9e333da735dd75e97c4bc8206c9fa7cb9b2da5cd`. The exact root-retained artifact contains 12 files and 529,223 ZIP bytes, with SHA-256 `c41af803458b432eaa934e606169a76235488c65472bd4c27e41ac73a2deee56`. Offline analysis recomputed this hash against the root receipt and GitHub API digest, joined ZIP membership/member hashes to the extracted manifest, checked the reviewed V2 plan/template and all five owned source snapshots, and found zero integrity/consistency questions.

| Observed measure | Retained result |
| --- | --- |
| Allocated / unexecuted development tasks | 1 / 1 |
| Runtime preflight error | `ValueError: installed_distribution_version_mismatch` |
| Upstream provider allocations | 0 |
| Original ADK events / business tools | 0 / 0 |
| Original native launch / receipt observations | 0 / 0 |
| Provider handler drain | Not started because runtime preflight failed |
| Required package versions matching the pip install report | 182 / 182 |
| Total pip install-report distributions | 184 |
| Additional Linux report distributions | `jeepney`, `secretstorage` |
| Pip dependency check | `No broken requirements found.` |
| Actual selected-interpreter distribution census | Absent from this artifact |
| Whole-task semantic grade | `null` |

The archived pip report has no missing or differently versioned required distribution. Its two additional Linux distributions do not explain the required-version comparison failure: the inherited checker compares required entries, rather than requiring an identical distribution set. The pip report and dependency check describe installation/report evidence; the selected interpreter's actual metadata was not retained after the preflight exception, so exact runtime version mismatches remain unknown.

The frozen source establishes a launcher regression. V1's retained runner at line 329 passes `args.python.absolute()` to execution. V2's retained runner at line 209 instead passes `args.python.resolve()`. On Linux, a virtual-environment `bin/python` is commonly a symlink; resolving it can select the global interpreter path and lose the virtual environment's interpreter context. The inherited helper at line 347 executes the supplied Python path to collect distribution metadata, then raises the retained comparison error at line 353 before writing `portable-runtime.json`. This source-derived failure mode explains how the report can match required versions while the selected-interpreter preflight fails. The artifact does not independently record the actual resolved interpreter or its mismatched versions.

The path-normalization change was introduced in the owned V2 launcher. The frozen V2 source and this failed record remain preserved. A separate V3 successor restores the absolute virtual-environment launcher path and adds CLI/symlink regression controls; V3 outcomes belong to that new allocation and cannot replace this unexecuted V2 task.

Actual V2 reconstruction is retained at [offline-analysis-43045731741-1/analysis.json](../../runs/ap2-native-shopper-provider-development/v2/offline-analysis-43045731741-1/analysis.json). The explicit outcome is `runtime_preflight_failed_before_provider_or_application_calls`, with one-case denominator, zero allocations and the original preflight error. [source-diagnosis.json](../../runs/ap2-native-shopper-provider-development/v2/offline-analysis-43045731741-1/source-diagnosis.json) separately retains pip-report joins, source line references/hashes and the absent-runtime limitation. Neither result is a constructed substitute for actual evidence.

The new V2 analyzer uses the unchanged V1 observation helpers and requires explicit actual run/full-head inputs. It checks stable capture/drain records when the boundary starts, distinguishing active/queued handlers from consumed allocations and keeping unfinished consumed allocations unknown. This actual run reaches its explicit partial-preflight branch, where absent provider/drain/application records are expected.

Nineteen constructed analyzer controls pass under `python -I -S -B`, including the full partial-preflight branch with retained failure, one unexecuted case and zero calls. Other controls cover V2 schema/source/template binding, denominator, normal/incomplete drain, late handler completion with unknown consumption, queued handlers, contradictory completed-capture claims, post-freeze ledger timestamps, altered counts/bounds and measurement claims with inconsistent provider summaries. They execute only owned standard-library analysis; original SDKs, applications, listeners and providers are not executed by these controls.

The 15 frozen V2 sender/lifecycle controls remain separate software verification. V2's actual failed preflight does not establish live sender or handler-drain success. Human semantic gold, held-out-study credit, original `run.sh` provisioning qualification, signature/hidden-effect validation and settlement proof remain absent.
