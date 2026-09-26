import codecs

file_path = r"c:\Xaiote\backend\tests\test_phase_4d_analysis.py"
with codecs.open(file_path, "r", "utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "`n" in line:
        # Split by `n and just keep the original parts if we want, or clean it.
        # Actually it looks like a crazy string `n    await db.execute(...)
        # We can just extract the last clean command.
        parts = line.split("`n")
        new_lines.append(parts[-1].lstrip(" ") + "\n")
    else:
        new_lines.append(line)

with codecs.open(file_path, "w", "utf-8") as f:
    f.writelines(new_lines)
