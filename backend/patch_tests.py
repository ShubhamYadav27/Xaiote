import os

files = [
    "tests/test_phase_4a_impact.py",
    "tests/test_phase_4b_api.py",
    "tests/test_phase_4c_incidents.py",
    "tests/test_phase_4d_analysis.py",
    "tests/test_work_orders.py",
    "tests/test_worker.py",
    "tests/test_communication.py",
    "tests/test_imports.py",
    "tests/test_masters.py",
    "tests/test_phase_3f_revisions.py",
    "tests/test_phase_3f_validation.py",
    "tests/test_phase_3g_verification.py",
]

for f in files:
    if not os.path.exists(f):
        continue
    with open(f, "r") as file:
        content = file.read()

    if "DELETE FROM whatsapp_integrations" not in content and "DELETE FROM " in content:
        # Find the last DELETE FROM statement and append our deletions after it
        lines = content.splitlines()
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if "DELETE FROM " in line and "DELETE FROM " not in (
                lines[i + 1] if i + 1 < len(lines) else ""
            ):
                # This is the last delete in a block
                indent = line[: len(line) - len(line.lstrip())]
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM assessment_decision_history"))'
                )
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM assessment_evidence_links"))'
                )
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM root_cause_assessments"))'
                )
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM incident_analyses"))'
                )
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM whatsapp_integrations"))'
                )
                new_lines.append(
                    f'{indent}await db.execute(text("DELETE FROM authorized_senders"))'
                )

        with open(f, "w") as file:
            file.write("\n".join(new_lines) + "\n")
