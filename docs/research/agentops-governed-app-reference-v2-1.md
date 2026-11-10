# Six governed-App references v2.1: source prerequisite repair

Hosted v2 run `42880999920` stopped during constructed evaluator controls before SDK/App execution because the Git checkout omits the original ignored seed database. The controls require a checksum-pinned read-only source fixture; installing the runtime after those controls cannot supply it in time. This attempt is retained as a preparation failure and supplies no new App result.

The separate v2.1 workflow first downloads the checksum-pinned original source archive and verifies its 421 regular members in an exclusive temporary root. It preflights every existing source member for the exact original bytes, rejects symlinks and extra files, creates only missing checkout members with exclusive-create, and verifies the complete original inventory. It never overwrites an existing member. The original actor, evaluator and their controls remain unchanged.

The new coordinator requires the same-run successful source-stage receipt and verified checkout bytes, retains source-stage evidence, then uses the same verified original archive for a separately allocated locked runtime. The original hosted memory gate and strict socket denials remain in force. Both source-stage and reference artifacts upload even when later steps fail. The new allocation does not overwrite or retry the old capture.

Use `.github/workflows/agentops-governed-app-reference-v2-1.yml`. V3 uses the same source prerequisite. This repairs a hosted preparation dependency; source staging and constructed controls do not establish task execution, validated gold or provider/held-out quality.
