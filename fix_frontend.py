import os
for f in ["frontend/src/app/(dashboard)/events/page.tsx", "frontend/src/app/(dashboard)/events/[id]/page.tsx"]:
    with open(f, "r", encoding="utf-8") as file:
        c = file.read()
    c = c.replace(r"\/events/?\${params.toString()}\`", r"`/events/?${params.toString()}`")
    c = c.replace(r"\/events/\${id}\`", r"`/events/${id}`")
    c = c.replace(r"\/events/\${id}/revisions\`", r"`/events/${id}/revisions`")
    c = c.replace(r"\`\${field.key}_provenance\`", r"`${field.key}_provenance`")
    c = c.replace(r"\`text-[10px] px-1.5 py-0.5 rounded ml-2 \${", r"`text-[10px] px-1.5 py-0.5 rounded ml-2 ${")
    c = c.replace(r"}\`", r"}`")
    c = c.replace(r"\`\${total} total event\${total !== 1 ? " + chr(34) + "s" + chr(34) + " : " + chr(34) + chr(34) + "}\`", r"`${total} total event${total !== 1 ? " + chr(34) + "s" + chr(34) + " : " + chr(34) + chr(34) + "}`")
    c = c.replace(r"\`inline-block px-2.5 py-1 rounded-md text-xs font-semibold \${getSeverityColor(event.severity)}\`", r"`inline-block px-2.5 py-1 rounded-md text-xs font-semibold ${getSeverityColor(event.severity)}`")
    c = c.replace(r"\`inline-block px-2.5 py-1 rounded-md text-xs font-semibold \${getStatusColor(event.event_status)}\`", r"`inline-block px-2.5 py-1 rounded-md text-xs font-semibold ${getStatusColor(event.event_status)}`")
    c = c.replace(r"\`/events/\${event.id}\`", r"`/events/${event.id}`")
    with open(f, "w", encoding="utf-8") as file:
        file.write(c)
