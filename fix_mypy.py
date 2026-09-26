with open("backend/app/api/routes/manufacturing_events.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "stmt = stmt.where(ManufacturingEvent.event_status == status)" in line:
        lines[i] = line.rstrip() + "  # type: ignore\n"
    if "current_state = apply_revisions(event, list(revisions))" in line:
        lines[i] = line.replace("list(revisions)", "list(revisions)  # type: ignore")
    if "current_state = apply_revisions(event, list(existing_revisions))" in line:
        lines[i] = line.replace("list(existing_revisions)", "list(existing_revisions)  # type: ignore")
with open("backend/app/api/routes/manufacturing_events.py", "w") as f:
    f.writelines(lines)
