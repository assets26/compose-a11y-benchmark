"""Additional Compose accessibility detectors (Study 2, extended category set).
Each returns (category, evidence) tuples. Deliberately over-inclusive:
output is CANDIDATES for human judgment, never verdicts."""
import re

def flag_extended(body):
    hits = []

    # A. pointerInput tap gesture with no semantics -> invisible to TalkBack
    for m in re.finditer(r"\.pointerInput\s*\(", body):
        seg = body[m.start():m.start() + 500]
        if re.search(r"detectTapGestures|detectDragGestures", seg):
            ctx = body[max(0, m.start() - 300):m.start() + 500]
            if not re.search(r"\.semantics|Role\.|onClickLabel|\.clickable", ctx):
                hits.append(("pointerinput_no_semantics",
                             "detectTapGestures without semantics/Role"))

    # B. TextField with placeholder but no label
    for m in re.finditer(r"\b(OutlinedTextField|TextField|BasicTextField)\s*\(", body):
        seg = body[m.start():m.start() + 700]
        if "placeholder" in seg and "label" not in seg:
            hits.append(("textfield_no_label",
                         f"{m.group(1)} with placeholder but no label"))

    # C. maxLines=1 + ellipsis -> truncation under font scaling
    for m in re.finditer(r"maxLines\s*=\s*1\b", body):
        seg = body[max(0, m.start() - 400):m.start() + 400]
        if "TextOverflow.Ellipsis" in seg and re.search(r"\bText\s*\(", seg):
            hits.append(("text_truncation_scaling",
                         "maxLines = 1 with Ellipsis (clips at large font scale)"))

    # D. Heading-styled Text without heading() semantics
    for m in re.finditer(r"(headlineLarge|headlineMedium|headlineSmall|titleLarge)", body):
        seg = body[max(0, m.start() - 500):m.start() + 500]
        if "heading()" not in seg:
            hits.append(("missing_heading_semantics",
                         f"{m.group(1)} text without heading()"))

    # E. Composite clickable container without mergeDescendants
    for m in re.finditer(r"\b(Row|Column|Card|ListItem)\s*\(", body):
        seg = body[m.start():m.start() + 900]
        n_text = len(re.findall(r"\bText\s*\(", seg))
        clickable = ".clickable" in seg or "onClick" in seg
        if clickable and n_text >= 2 and "mergeDescendants" not in seg \
           and "clearAndSetSemantics" not in seg:
            hits.append(("missing_merge_descendants",
                         f"clickable {m.group(1)} with {n_text} Text children, no mergeDescendants"))

    # F. Progress indicator without progressSemantics
    for m in re.finditer(r"\b(LinearProgressIndicator|CircularProgressIndicator)\s*\(", body):
        seg = body[max(0, m.start() - 300):m.start() + 400]
        if "progressSemantics" not in seg and "contentDescription" not in seg:
            hits.append(("progress_no_semantics",
                         f"{m.group(1)} without progressSemantics"))

    # G. isError without error() semantics
    for m in re.finditer(r"isError\s*=\s*(?!false)", body):
        seg = body[max(0, m.start() - 500):m.start() + 600]
        if not re.search(r"semantics\s*\{[^}]*error\s*\(", seg):
            hits.append(("error_state_no_semantics",
                         "isError set without semantics { error(...) }"))

    # H. Clickable Icon not wrapped in IconButton (role + 48dp both at risk)
    for m in re.finditer(r"\bIcon\s*\(", body):
        seg = body[max(0, m.start() - 250):m.start() + 250]
        if ".clickable" in seg and "IconButton" not in seg:
            hits.append(("clickable_icon_not_iconbutton",
                         "Icon made clickable directly instead of IconButton"))
    return hits
