#!/usr/bin/env python3
import re
import sys
import os


def usage():
    print("%s <file.tex/path> [-x <excluded-switch1>] [-i <included-switch1>] [-i/x <switch n, evaluated in order of specification>] [--error]" % sys.argv[0])
    sys.exit(1)

if len(sys.argv) < 2:
    usage()
    

tex_files = []

if(not sys.argv[1].endswith(".tex")):
    for path, subdirs, files in os.walk(sys.argv[1]):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.join(path,f))
else:
    tex_files = [sys.argv[1]]

tex = None
tex_lines = None
tex_lines_clean = None
tex_lines_math_masked = None
tex_lines_math_texttt_masked = None
in_env = None
envs = None

FLOAT_ENVS = ["figure", "listing", "table"]
CODE_WARNING_EXCEPTIONS = {
    "listing-alignment",
    "listing-label",
    "listing-caption",
    "listing-caption-order",
    "listing-float",
}
SECTION_COMMAND_RE = re.compile("\\\\(section|subsection|subsubsection|paragraph)\\*?\\{([^\\}]+)\\}")
SENTENCE_END_RE = re.compile(r"(?<!\\)[.!?](?=(?:['\")\]}]*)(?:\s|$))")
    
def next_file(file):
    global tex, tex_lines, tex_lines_clean, tex_lines_math_masked, tex_lines_math_texttt_masked, in_env, envs
    try:
        tex = open(file).read()
    except:
        print("Could not open '%s'" % sys.argv[1])
        sys.exit(1)

    tex_lines = tex.split("\n")
    tex_lines_clean = tex.split("\n")
    tex_lines_math_masked = tex.split("\n")
    tex_lines_math_texttt_masked = tex.split("\n")
    in_env = {}
    envs = {}


def preprocess():
    global tex_lines_math_masked, tex_lines_math_texttt_masked
    env = list(set(re.findall(r"\\begin\{(\w+)\*?\}", tex)))
    for e in env:
        in_env[e] = []
        envs[e] = []
        current_start = -1
        begin_pattern = re.compile(r"\\begin\{%s\*?\}" % re.escape(e))
        end_pattern = re.compile(r"\\end\{%s\*?\}" % re.escape(e))
        for i, l in enumerate(tex_lines):
            if begin_pattern.search(l):
                in_env[e].append(True)
                current_start = i
            elif end_pattern.search(l):
                in_env[e].append(False)
                envs[e].append((current_start, i))
            else:
                if len(in_env[e]) == 0:
                    in_env[e].append(False)
                else:
                    in_env[e].append(in_env[e][-1])
            if "%" in tex_lines[i]:
                idx = tex_lines[i].index("%")
                if idx > 0 and tex_lines[i][idx - 1] != "\\":
                    tex_lines_clean[i] = tex_lines[i][0:max(0, (tex_lines[i].index("%") - 1))]
                    if tex_lines_clean[i].startswith("%"): tex_lines_clean[i] = ""
                else:
                    tex_lines_clean[i] = tex_lines[i]
            else:
                tex_lines_clean[i] = tex_lines[i]
    if "comment" in in_env:
        for i in range(len(tex_lines_clean)):
            if in_env["comment"][i]:
                tex_lines_clean[i] = ""
    tex_lines_math_masked = mask_math_in_lines(tex_lines_clean)
    tex_lines_math_texttt_masked = [
        mask_spans(line, get_command_brace_spans(line, "texttt"))
        for line in tex_lines_math_masked
    ]


def in_any_env(line):
    for e in in_env:
        if in_env[e][line]:
            return True
    return False


def in_any_float(line):
    for f in FLOAT_ENVS:
        if f in in_env and in_env[f][line]:
            return True
    return False

def in_code(line):
    if "lstlisting" in in_env:
        return in_env["lstlisting"][line]
    return False

def in_comment(line):
    if "comment" in in_env:
        return in_env["comment"][line]
    return False

def in_list(line):
    for env in ["itemize", "enumerate", "compactitem", "compactenum", "description"]:
        if env in in_env and in_env[env][line]:
            return True
    return False

def in_equation(line):
    if "equation" in in_env and in_env["equation"][line]:
        return True
    if "align" in in_env and in_env["align"][line]:
        return True
    if "align*" in in_env and in_env["align*"][line]:
        return True
    if "eqnarray" in in_env and in_env["eqnarray"][line]:
        return True
    if "theorem" in in_env and in_env["theorem"][line]:
        return True
    if "proof" in in_env and in_env["proof"][line]:
        return True
    if "proposition" in in_env and in_env["proposition"][line]:
        return True
    
    return False


def normalize_title(title):
    return re.sub("\\s+", " ", title.strip()).lower()


def get_section_entries():
    entries = []
    for i, l in enumerate(tex_lines_clean):
        match = SECTION_COMMAND_RE.search(l)
        if match:
            entries.append({
                "line": i,
                "level": match.group(1),
                "title": match.group(2).strip(),
                "span": match.span(),
                "starred": "*" in match.group(0)
            })
    return entries


def extract_section_ranges():
    entries = [e for e in get_section_entries() if e["level"] == "section"]
    appendix_line = tex.find("\\appendix")
    appendix_line = tex[:appendix_line].count("\n") if appendix_line != -1 else None
    ranges = []
    for idx, entry in enumerate(entries):
        start = entry["line"] + 1
        end = len(tex_lines)
        for nxt in entries[idx + 1:]:
            end = nxt["line"]
            break
        ranges.append({
            "title": entry["title"],
            "line": entry["line"],
            "span": entry["span"],
            "starred": entry["starred"],
            "in_appendix": appendix_line is not None and entry["line"] > appendix_line,
            "start": start,
            "end": end
        })
    return ranges


def count_sentences(text):
    stripped = text.strip()
    if not stripped:
        return 0
    cleaned = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", " ", stripped)
    return len(SENTENCE_END_RE.findall(cleaned))


def is_paragraph_content(line):
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("%"):
        return False
    if stripped in ["{", "}"]:
        return False
    if re.match("\\\\(section|subsection|subsubsection|paragraph|begin|end|item|label|caption|centering|bibliography|bibliographystyle|appendix|FloatBarrier|clearpage|cleardoublepage|maketitle|title|author|date|thanks|if|else|fi|newcommand|renewcommand|providecommand|definecolor|newlength|setlength|AtBeginDocument)\\b", stripped):
        return False
    return True


def get_paragraphs(start=0, end=None):
    if end is None:
        end = len(tex_lines_clean)
    paragraphs = []
    para_start = None
    para_lines = []
    for idx in range(start, end):
        if "document" in in_env and not in_env["document"][idx]:
            continue
        stripped = tex_lines_clean[idx].strip()
        if stripped.startswith("%"):
            continue
        if in_code(idx) or in_equation(idx) or in_any_float(idx):
            if para_lines:
                paragraphs.append((para_start, idx, " ".join(para_lines).strip()))
                para_start = None
                para_lines = []
            continue
        item_match = re.match(r"\\item(?:\s*\[[^\]]+\])?\s*(.*)", stripped)
        if item_match:
            if para_lines:
                paragraphs.append((para_start, idx, " ".join(para_lines).strip()))
            para_start = idx
            para_lines = [item_match.group(1).strip()]
            continue
        if is_paragraph_content(tex_lines_clean[idx]):
            if para_start is None:
                para_start = idx
            para_lines.append(stripped)
        else:
            if para_lines:
                paragraphs.append((para_start, idx, " ".join(para_lines).strip()))
                para_start = None
                para_lines = []
    if para_lines:
        paragraphs.append((para_start, end, " ".join(para_lines).strip()))
    return paragraphs


def get_math_spans(line):
    spans = []
    for pattern in [r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", r"\\\((.+?)\\\)"]:
        for match in re.finditer(pattern, line):
            spans.append((match.start(), match.end(), match.group(1)))
    return spans


def mask_spans(line, spans):
    if not spans:
        return line
    chars = list(line)
    for start, end in spans:
        for pos in range(max(0, start), min(len(chars), end)):
            chars[pos] = " "
    return "".join(chars)


def get_inline_math_spans(line):
    spans = []
    i = 0
    math_start = None
    while i < len(line):
        if line.startswith(r"\(", i):
            if math_start is None:
                math_start = i
            else:
                spans.append((math_start, i + 2))
                math_start = None
            i += 2
            continue
        if line[i] == "$" and (i == 0 or line[i - 1] != "\\"):
            if math_start is None:
                math_start = i
            else:
                spans.append((math_start, i + 1))
                math_start = None
        i += 1
    return spans


def get_command_brace_spans(line, command):
    spans = []
    pattern = re.compile(r"\\%s\*?\{" % re.escape(command))
    for match in pattern.finditer(line):
        start = match.start()
        pos = match.end() - 1
        depth = 0
        while pos < len(line):
            char = line[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    spans.append((start, pos + 1))
                    break
            pos += 1
    return spans


def mask_math_in_lines(lines):
    masked_lines = []
    state = None
    for line in lines:
        chars = list(line)
        i = 0
        while i < len(line):
            if state is None:
                if line.startswith(r"\(", i):
                    chars[i:i + 2] = [" ", " "]
                    state = r"\("
                    i += 2
                    continue
                if line.startswith(r"\[", i):
                    chars[i:i + 2] = [" ", " "]
                    state = r"\["
                    i += 2
                    continue
                if line.startswith("$$", i) and (i == 0 or line[i - 1] != "\\"):
                    chars[i:i + 2] = [" ", " "]
                    state = "$$"
                    i += 2
                    continue
                if line[i] == "$" and (i == 0 or line[i - 1] != "\\"):
                    chars[i] = " "
                    state = "$"
            else:
                if state == r"\(" and line.startswith(r"\)", i):
                    chars[i:i + 2] = [" ", " "]
                    state = None
                    i += 2
                    continue
                if state == r"\[" and line.startswith(r"\]", i):
                    chars[i:i + 2] = [" ", " "]
                    state = None
                    i += 2
                    continue
                if state == "$$" and line.startswith("$$", i) and (i == 0 or line[i - 1] != "\\"):
                    chars[i:i + 2] = [" ", " "]
                    state = None
                    i += 2
                    continue
                if state == "$" and line[i] == "$" and (i == 0 or line[i - 1] != "\\"):
                    chars[i] = " "
                    state = None
                    i += 1
                    continue
                chars[i] = " "
            i += 1
        masked_lines.append("".join(chars))
    return masked_lines


def mask_inline_math(line):
    return mask_spans(line, get_inline_math_spans(line))


def mask_inline_math_and_texttt(line):
    spans = get_inline_math_spans(line)
    spans.extend(get_command_brace_spans(line, "texttt"))
    return mask_spans(line, spans)


def strip_explicit_math_text(content):
    stripped = content
    explicit_text_commands = [
        "text",
        "textrm",
        "textit",
        "textbf",
        "textsf",
        "texttt",
        "textsc",
        "mbox",
        "operatorname",
        "mathrm",
        "mathit",
        "mathbf",
        "mathsf",
        "mathtt",
        "mathcal",
        "mathbb",
        "mathfrak",
    ]
    pattern = re.compile(r"\\(?:%s)\*?\{[^{}]*\}" % "|".join(explicit_text_commands))
    while True:
        updated = pattern.sub(" ", stripped)
        if updated == stripped:
            return stripped
        stripped = updated

def check_space_before_cite():
    warns = []
    for i, l in enumerate(tex_lines):
        b = re.search("[^ ~]\\\\cite", l)
        if b:
            if not "\\etal\\cite" in l:
                warns.append((i, "No space before \\cite", b.span(0)))
    return warns

def check_float_alignment(env):
    warns = []
    for i, l in enumerate(tex_lines):
        b = re.search(r"\\begin\{%s\}" % env, l)
        if b:
            if not re.search(r"%s}\[[^\]]*[htbH][^\]]*\]" % env, l):
                warns.append((i, "%s without alignment: %s" % (env, l.strip()), b.span()))
    return warns

def check_figure_alignment():
    return check_float_alignment("figure")

def check_table_alignment():
    return check_float_alignment("table")

def check_listing_alignment():
    return check_float_alignment("listing")

def check_float_has_label(env):
    warns = []
    if env not in envs: return warns
    for r in envs[env]:
        label = False
        for i in range(*r):
            b = re.search(r"\\label\{", tex_lines[i])
            if b:
                label = True
        if not label:
            warns.append((r[0], "%s without a label" % env))
    return warns


def check_float_has_caption(env):
    warns = []
    if env not in envs: return warns
    for r in envs[env]:
        label = False
        for i in range(*r):
            b = re.search(r"\\caption\{", tex_lines[i])
            if b:
                label = True
        if not label:
            warns.append((r[0], "%s without a caption" % env))
    return warns

def check_float_caption_label_order(env):
    warns = []
    if env not in envs: return warns
    for r in envs[env]:
        label = -1
        caption = -1
        for i in range(*r):
            b = re.search(r"\\caption\{", tex_lines[i])
            if b:
                caption = i
            b = re.search(r"\\label\{", tex_lines[i])
            if b:
                label = i
        if label > -1 and caption > -1 and label < caption:
            warns.append((r[0], "label before caption in %s, swap for correct references" % env))
    return warns


def check_no_resizebox_for_tables():
    warns = []
    if "table" not in envs: return warns
    for r in envs["table"]:
        rb = False
        b = None
        for i in range(*r):
            b = re.search(r"\\resizebox\{", tex_lines[i])
            if b:
                rb = True
                break
        if rb:
            warns.append((r[0], "table with resizebox -> use adjustbox instead"))
    return warns


def check_weird_units():
    warns = []
    block = ["\\textwidth", "\\linewidth"]
    for i, l in enumerate(tex_lines):
        for b in block:
            if b in l:
                warns.append((i, "use \\hsize instead of %s" % b, (l.index(b), l.index(b) + len(b))))
    return warns

def check_figure_has_label():
    return check_float_has_label("figure")

def check_table_has_label():
    return check_float_has_label("table")

def check_listing_has_label():
    return check_float_has_label("listing")

def check_figure_has_caption():
    return check_float_has_caption("figure")

def check_table_has_caption():
    return check_float_has_caption("table")

def check_listing_has_caption():
    return check_float_has_caption("listing")

def check_figure_caption_label_order():
    return check_float_caption_label_order("figure")

def check_table_caption_label_order():
    return check_float_caption_label_order("table")

def check_listing_caption_label_order():
    return check_float_caption_label_order("listing")

def check_todos():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        if "TODO" in l:
            warns.append((i, "TODO found", (l.index("TODO"), l.index("TODO") + 4)))
    return warns


def check_notes():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        if "\\note" in l:
            warns.append((i, "\\note found", (l.index("\\note"), l.index("\\note") + 5)))
        if "\\todo" in l:
            warns.append((i, "\\todo found", (l.index("\\todo"), l.index("\\todo") + 5)))
    return warns


def check_math_numbers():
    warns = []
    for i, l in enumerate(tex_lines):
        if in_code(i):
            continue
        n = re.search("\\$\\d+\\$", tex_lines[i]) 
        if n and not in_any_float(i):
            warns.append((i, "Number in math mode, consider using siunit instead", n.span()))
    return warns


def check_math_text_mix():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        if in_code(i):
            continue
        for start, end, content in get_math_spans(l):
            normalized = strip_explicit_math_text(content)
            normalized = re.sub("\\\\[A-Za-z]+", " ", normalized)
            normalized = re.sub("[\\^_{}&=+\\-*/(),.;:0-9\\s]", " ", normalized)
            words = re.findall("[A-Za-z]{2,}", normalized)
            prose_words = [word for word in words if word.islower()]
            prose_like_words = [word for word in prose_words if len(word) >= 4]
            if prose_like_words:
                warns.append((i, "Text-like content in math mode, mark it explicitly with \\text{...}", (start, end)))
                break
    return warns


def check_units():
    warns = []
    unit_pattern = re.compile(r"(?<!\\)(\b\d+(?:\.\d+)?)(\s?)(ms|ns|us|s|min|h|Hz|kHz|MHz|GHz|B|KB|MB|GB|TB|bit|m|cm|mm|km|g|kg|mg|V|A|W|kW|J|N|K|mol|cd)\b")
    for i, l in enumerate(tex_lines_clean):
        if in_code(i):
            continue
        if any(cmd in l for cmd in ["\\SI{", "\\si{", "\\qty{", "\\unit{"]):
            continue
        masked = tex_lines_math_masked[i]
        match = unit_pattern.search(masked)
        if match:
            before = masked[match.start() - 1] if match.start() > 0 else ""
            after = masked[match.end()] if match.end() < len(masked) else ""
            if before.isalnum() or before in ["-", "_"]:
                continue
            if after.isalnum() or after in ["-", "_"]:
                continue
            prefix = masked[:match.start()].rstrip()
            if re.search(r"\\[A-Za-z@]+\*?(?:\{[^{}]*\})*\{$", prefix):
                continue
            if re.search(r"(?:^|[,\[])\s*[A-Za-z@][A-Za-z0-9@ _-]*=\s*$", prefix):
                continue
            if match.group(2) == "":
                warns.append((i, "Unit attached to number, separate it and prefer siunitx", match.span()))
            else:
                warns.append((i, "Number with unit should use siunitx", match.span()))
    return warns


def check_float_placement():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        match = re.search("\\\\begin\\{(%s)\\}\\[([^\\]]*[hH][^\\]]*)\\]" % "|".join(FLOAT_ENVS), l)
        if match:
            warns.append((i, "Float uses discouraged placement specifier [%s]" % match.group(2), match.span(2)))
    return warns


def check_unused_macro():
    warns = []
    definitions = []
    patterns = [
        re.compile("\\\\newcommand\\*?\\{\\\\([A-Za-z@]+)\\}"),
        re.compile("\\\\providecommand\\*?\\{\\\\([A-Za-z@]+)\\}"),
        re.compile("\\\\def\\\\([A-Za-z@]+)")
    ]
    for i, l in enumerate(tex_lines_clean):
        for pattern in patterns:
            match = pattern.search(l)
            if match:
                definitions.append((match.group(1), i, match.span(1)))
                break
    for name, line, span in definitions:
        if len(re.findall("\\\\%s\\b" % re.escape(name), tex)) <= 1:
            warns.append((line, "Macro \\%s is defined but never used" % name, span))
    return warns


def check_required_sections():
    warns = []
    sections = {normalize_title(section["title"]) for section in extract_section_ranges()}
    if "\\begin{abstract}" in tex:
        sections.add("abstract")
    required = ["abstract", "introduction", "conclusion"]
    missing = [section.title() for section in required if section not in sections]
    if missing:
        warns.append((-1, "Missing required paper components: %s" % ", ".join(missing)))
    return warns


def check_section_balance():
    warns = []
    sections = extract_section_ranges()
    if len(sections) < 2:
        return warns
    word_counts = []
    filtered_sections = [section for section in sections if not section["starred"] and not section["in_appendix"]]
    if len(filtered_sections) < 2:
        return warns
    for section in filtered_sections:
        text = " ".join(tex_lines_clean[section["start"]:section["end"]])
        word_counts.append(len(re.findall("\\b\\w+\\b", text)))
    sorted_counts = sorted(word_counts)
    median = sorted_counts[len(sorted_counts) // 2]
    if median == 0:
        return warns
    for section, count in zip(filtered_sections, word_counts):
        if count < max(40, int(median * 0.3)):
            warns.append((section["line"], "Section '%s' is extremely short compared to the rest of the paper" % section["title"], section["span"]))
        elif count > max(600, int(median * 2.5)):
            warns.append((section["line"], "Section '%s' is extremely long compared to the rest of the paper" % section["title"], section["span"]))
    return warns


def check_deprecated():
    warns = []
    patterns = [
        (re.compile("\\{\\\\bf\\b"), "Deprecated font switch \\bf, use \\textbf{...}"),
        (re.compile("\\{\\\\it\\b"), "Deprecated font switch \\it, use \\textit{...}"),
        (re.compile("\\{\\\\rm\\b"), "Deprecated font switch \\rm, use \\textrm{...}"),
        (re.compile("\\{\\\\sc\\b"), "Deprecated font switch \\sc, use \\textsc{...}"),
        (re.compile("\\{\\\\tt\\b"), "Deprecated font switch \\tt, use \\texttt{...}"),
        (re.compile("\\$\\$"), "Deprecated display math $$...$$, use \\[...\\] or an equation environment"),
        (re.compile("\\\\centerline\\b"), "Deprecated \\centerline command"),
        (re.compile("\\\\epsfig\\b"), "Deprecated \\epsfig command, use \\includegraphics")
    ]
    for i, l in enumerate(tex_lines_clean):
        for pattern, message in patterns:
            match = pattern.search(l)
            if match:
                warns.append((i, message, match.span()))
    return warns


def check_package_conflict():
    warns = []
    packages = {}
    for i, l in enumerate(tex_lines_clean):
        for match in re.finditer("\\\\usepackage(?:\\[[^\\]]+\\])?\\{([^\\}]+)\\}", l):
            for package in [p.strip() for p in match.group(1).split(",")]:
                packages[package] = i
    conflicts = [
        ("subfigure", "subcaption"),
        ("subfig", "subcaption"),
        ("natbib", "biblatex")
    ]
    for left, right in conflicts:
        if left in packages and right in packages:
            warns.append((packages[right], "Conflicting packages loaded together: %s and %s" % (left, right)))
    return warns


def check_duplicate_word():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        if in_code(i):
            continue
        match = re.search("\\b(\\w+)\\s+\\1\\b", l, re.IGNORECASE)
        if match:
            warns.append((i, "Duplicated adjacent word '%s'" % match.group(1), match.span()))
    return warns


def check_paragraph_length():
    warns = []
    for start, end, text in get_paragraphs():
        if in_list(start):
            continue
        if not re.search("[.!?]", text):
            continue
        sentence_count = count_sentences(text)
        if sentence_count == 2:
            warns.append((start, "Paragraph has only %d sentence%s; expected at least 3" % (sentence_count, "" if sentence_count == 1 else "s"), (0, len(tex_lines[start]))))
    return warns


def check_section_length():
    warns = []
    for section in extract_section_ranges():
        if section["starred"] or section["in_appendix"]:
            continue
        paragraphs = [p for p in get_paragraphs(section["start"], section["end"]) if p[0] >= section["start"] and p[0] < section["end"]]
        if len(paragraphs) < 3:
            warns.append((section["line"], "Section '%s' has only %d paragraph%s; expected at least 3" % (section["title"], len(paragraphs), "" if len(paragraphs) == 1 else "s"), section["span"]))
    return warns


def check_subsection_count_sanity():
    warns = []
    sections = extract_section_ranges()
    for idx, section in enumerate(sections):
        if section["starred"] or section["in_appendix"]:
            continue
        next_line = sections[idx + 1]["line"] if idx + 1 < len(sections) else len(tex_lines)
        count = 0
        for line_no in range(section["start"], next_line):
            if re.search("\\\\subsection\\*?\\{", tex_lines_clean[line_no]):
                count += 1
        if count == 1 or count > 10:
            warns.append((section["line"], "Section '%s' has %d subsection%s; expected 0 or between 2 and 10" % (section["title"], count, "" if count == 1 else "s"), section["span"]))
    return warns


def check_large_numbers_without_si():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search(r"[\s(]\d{5,}[\s),\.]", tex_lines[i]) 
        if n and not in_any_float(i):
            warns.append((i, "Large number without formating, consider using siunit", n.span()))
    return warns

def check_env_not_in_float(env, float_env):
    warns = []
    if env in envs:
        for e in envs[env]:
            if (float_env not in in_env) or (not in_env[float_env][e[0]]):
                warns.append((e[0], "%s not within %s environment" % (env, float_env)))
    return warns
    

def check_listing_in_correct_float():
    return check_env_not_in_float("lstlisting", "listing")

def check_tabular_in_correct_float():
    return check_env_not_in_float("tabular", "table")

def check_tikz_in_correct_float():
    return check_env_not_in_float("tikzpicture", "figure")


def check_comment_has_space():
    warns = []
    for i, l in enumerate(tex_lines):
        ls = l.strip()
        if "%" in ls:
            if ls[0] != "%":
                c = re.search("[^\\s\\\\\\}\\{%]+%", l)
                if c and not in_code(i):
                    warns.append((i, "Comment without a whitespace before", c.span()))
    return warns


def check_percent_without_siunix():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search("\\d+\\s*\\\\%", l)
        if n:
            warns.append((i, "Number with percent without siunit", n.span(0)))
    return warns


def check_short_form():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        n = re.search("[^`%]\\w+'[a-rt-z]", l)
        if n:
            warns.append((i, "Contracted form used", n.span()))
    return warns


def check_labels_referenced():
    warns = []
    labels = [] #re.findall("\\\\label\{([^\\}]+)\}", tex)
    for i, l in enumerate(tex_lines_clean):
        lab = re.search(r"\\label\{([^\}]+)\}", l)
        if lab:
            labels.append((lab.group(1), i, lab.span()))
    for lab in labels:
        found = False
        for i, l in enumerate(tex_lines):
            if ("ref{%s}" % lab[0]) in l:
                found = True
                break
        if not found:
            if not (lab[0].startswith("sec") or lab[0].startswith("subsec")):
                warns.append((lab[1], "Label %s is not referenced" % lab[0], lab[2]))
    return warns


def check_section_capitalization():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search("(section|paragraph)\\{([^\\}]+)\\}", l)
        if n:
            try:
                words = n.group(2).split(" ")
                for w in words:
                    if len(w) > 4 and w[0].islower():
                        warns.append((i, "Wrong capitalization of header", (l.index(w), l.index(w) + 1)))
                        break
            except:
                pass
    return warns


def check_quotation():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        ws = re.search("[^\\\\]\"\\w+", l)
        we = re.search("\\w+\"", l)
        if (ws or we) and not in_code(i):
            warns.append((i, "Wrong quotation, use `` and '' instead of \"", ws.span() if ws else we.span()))
    return warns


def check_hline_in_table():
    warns = []
    for i, l in enumerate(tex_lines):
        hl = re.search("\\\\hline", l)
        if hl:
            if "tabular" in in_env and in_env["tabular"]:
                warns.append((i, "\\hline in table, consider using \\toprule, \\midrule, \\bottomrule.", hl.span()))
    return warns


def check_space_before_punctuation():
    warns = []
    for i, l in enumerate(tex_lines):
        s = re.search("\\s+[,.!?:;]", l)
        if s and not in_any_env(i):
            warns.append((i, "Spacing before punctuation", s.span()))
    return warns


def check_headers_without_text():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search("(section|paragraph)\\{([^\\}]+)\\}", l)
        if n:
            nx = i
            while (nx + 1) < len(tex_lines):
                nx += 1
                if len(tex_lines[nx].strip()) == 0: continue
                if tex_lines[nx].strip().startswith("%"): continue
                nn = re.search("(section|paragraph)\\{([^\\}]+)\\}", tex_lines[nx])
                if nn:
                    warns.append((i, "Section header without text before next header", n.span()))
                break
    return warns


def check_one_sentence_paragraphs():
    warns = []
    for i, l in enumerate(tex_lines):
        if i > 0 and i < len(tex_lines) - 1:
            if len(tex_lines[i - 1].strip()) == 0 and len(tex_lines[i + 1].strip()) == 0 and len(tex_lines[i].strip()) > 0:
                if tex_lines[i].strip().startswith("\\"): continue
                if ". " in tex_lines[i]: continue
                warns.append((i, "One-sentence paragraph", (0, len(tex_lines[i]))))
    return warns


def check_multiple_sentences_per_line():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        p = re.search("[\\.!?]\\s+\\w+", l.rstrip())
        if p and "vs." not in l.rstrip():
            warns.append((i, "Multiple sentences in one line", p.span()))
    return warns


def check_unbalanced_brackets():
    warns = []
    for i, l in enumerate(tex_lines):
        if in_code(i):
            continue
        masked = tex_lines_math_masked[i]
        if masked.count("(") != masked.count(")"):
            first = min(masked.index("(") if masked.count("(") > 0 else len(masked), masked.index(")") if masked.count(")") > 0 else len(masked))
            last = max(masked.rindex("(") if masked.count("(") > 0 else len(masked), masked.rindex(")") if masked.count(")") > 0 else len(masked))
            warns.append((i, "Mismatch of opening and closing parenthesis", (first, last)))
    return warns


def check_and_or():
    warns = []
    for i, l in enumerate(tex_lines):
        ao = re.search("and/or", l)
        if ao:
            warns.append((i, "And/or discouraged in academic writing", ao.span()))
    return warns


def check_ellipsis():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        el = re.search("\\w+\\.\\.\\.", l)
        if el:
            warns.append((i, "Ellipsis \"...\" discouraged in academic writing", el.span()))
    return warns


def check_etc():
    warns = []
    for i, l in enumerate(tex_lines):
        el = re.search("\\s+etc[\\.\\w]", l)
        if el:
            warns.append((i, "Unspecific \"etc\" discouraged in academic writing", el.span()))
    return warns


def check_footnote():
    warns = []
    for i, l in enumerate(tex_lines):
        fn = re.search("\\s*\\\\footnote\\{[^\\}]+\\}\\.", l)
        if fn:
            warns.append((i, "Footnote must be after the full stop", fn.span()))
    return warns


def check_table_top_caption():
    warns = []
    if "table" in envs:
        for table in envs["table"]:
            caption = -1
            tab = -1
            for intab in range(*table):
                if re.search("\\\\caption\\{", tex_lines[intab]):
                   caption = intab
                if re.search("\\\\begin\\{tabular", tex_lines[intab]):
                    tab = intab
            if tab != -1 and caption != -1 and tab < caption:
                warns.append((table[0], "Table caption must be above table"))
    return warns



def check_punctuation_end_of_line():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        sl = l.strip()
        if len(sl) < 10: continue
        if len(sl.split(" ")) < 8: continue
        if in_any_float(i): continue
        if "lstlisting" in in_env and in_env["lstlisting"][i]: continue
        if sl.startswith("\\") or sl.startswith("%"): continue
        if sl.endswith("\\\\") or sl.endswith("}"): continue
        if sl.endswith(".") or sl.endswith("!") or sl.endswith("?") or sl.endswith(":") or sl.endswith(";"): continue
        p = re.search("\\s*[\\w})$]+[\\.!?}{:;\\\\]\\s*$", l.rstrip())
        if not p:
            warns.append((i, "Line ends without punctuation", (len(l) - 2, len(l))))
    return warns


def check_table_vertical_lines():
    warns = []
    for i, l in enumerate(tex_lines):
        t = re.search("\\\\begin\\{tabular\\}\\{([^\\}]+)\\}", l)
        if t and "|" in t.group(1):
            warns.append((i, "Vertical lines in tables are discouraged", t.span()))
    return warns


def check_will():
    warns = []
    for i, l in enumerate(tex_lines):
        w = re.search("\\s+will\\s+", l)
        if w:
            warns.append((i, "Usage of \"will\" is discouraged.", w.span()))
    return warns


def check_subsection_count():
    warns = []
    last_section = -1
    subsections = []
    for i, l in enumerate(tex_lines):
        if re.search("\\\\section{", l):
            if last_section != -1 and len(subsections) == 1:
                warns.append((last_section, "Section only has one subsection", re.search("\\\\section{", tex_lines[last_section]).span()))
            last_section = i
            subsections = []
        if re.search("\\\\subsection{", l):
            subsections.append(i)
    return warns


def check_mixed_compact_and_item():
    warns = []
    if "\\begin{compactenum}" in tex:
        for i, l in enumerate(tex_lines):
            it = re.search(r"\\begin\{enumerate\}", l)
            if it:
                warns.append((i, "compactenum mixed with enumerate", it.span()))
    if "\\begin{compactitem}" in tex:
        for i, l in enumerate(tex_lines):
            it = re.search(r"\\begin\{itemize\}", l)
            if it:
                warns.append((i, "compactitem mixed with itemize", it.span()))
    return warns


def check_center_in_float():
    warns = []
    if "center" in envs:
        for c in envs["center"]:
            if in_any_float(c[0]):
                warns.append((c[0], "Use \\centering instead of \\begin{center} inside floats", re.search(r"\\begin\{center\}", tex_lines[c[0]]).span()))
    return warns


def check_appendix():
    warns = []
    for i, l in enumerate(tex_lines):
        ap = re.search(r"\\begin\{appendix\}", l)
        if ap:
            warns.append((i, "Use \\appendix instead of \\begin{appendix}", ap.span()))
    return warns


def check_eqnarray():
    warns = []
    for i, l in enumerate(tex_lines):
        ap = re.search(r"\\begin\{eqnarray\}", l)
        if ap:
            warns.append((i, "Use \\begin{align} instead of \\begin{eqnarray}", ap.span()))
    return warns


def check_acm_pc():
    # based on https://www.acm.org/diversity-inclusion/words-matter
    warns = []
    replace = [
        ("\\bsupremacy\\b", "advantage"),
        ("\\bmaster\\b", "main/primary/leader/parent/host"),
        ("\\bslave\\b", "secondary/replica/follower/child/worker/client"),
        ("\\bhe\\b", "they"),
        ("\\bshe\\b", "they"),
        ("\\bhis\\b", "their"),
        ("\\bhers?\\b", "their/them"),
        ("\\bhim\\b", "them"),
        ("\\bmale\\bconnector\\b", "plug"),
        ("\\bfemale\\bconnector\\b", "socket"),
        ("\\bblind\\b", "anonymous"),
        ("\\bblack\\-?\\s?list\\b", "blocklist/unapprovedlist"),
        ("\\bwhite\\-?\\s?list\\b", "allowlist/approvedlist"),
        ("\\bblack\\-?\\s?hat\\b", "unethical attacker/hostile force"),
        ("\\bwhite\\-?\\s?hat\\b", "ethical attacker/friendly force"),
        ("\\bblack\\-?\\s?box\\b", "opaque box"),
        ("\\bwhite\\-?\\s?box\\b", "clear box"),
        ("\\baverage\\s?user\\b", "common/standard/typical user"),
        ("\\babort\\s?child\\b", "cancel/force quit/stop/end/finalize"),
        ("\\bterminate\\s?child\\b", "cancel/force quit/stop/end/finalize"),
        ("\\bdark\\-?\\s?pattern\\b", "deceptive design"),
        ("\\bdummy\\-?\\s?head\\b", "temporary head"),
        ("\\bgender\\-?\\s?bender\\b", "plug-socket adapter"),
        ("\\borphaned\\-?\\s?object\\b", "unreferenced/unlinked object"),
        ("\\bsanity\\-?\\s?check", "coherence/quick/well-formedness check")
    ]
    for i, l in enumerate(tex_lines):
        for r in replace:
            w = re.search(r[0], l)
            if w:
                warns.append((i, "Discouraged term \"%s\", consider replacing with \"%s\"" % (w.group(), r[1]), w.span()))
    return warns


def check_cite_noun():
    warns = []
    for i, l in enumerate(tex_lines):
        ap = re.search("\\b(in|from|by|and|or)[\\s~]\\\\cite", l.lower())
        if ap:
            warns.append((i, "Citation is used as noun", ap.span()))
        ap = re.search("^\\s*\\\\cite", l)
        if ap:
            warns.append((i, "Citation at the beginning of a sentence (probably as noun)", ap.span()))
    return warns


def check_cite_duplicate():
    warns = []
    for i, l in enumerate(tex_lines):
        cites = re.findall("\\\\(no)?citeA?\\{([^\\}]+)\\}", l)
        for cite in cites:
            c = [x.strip().split(",") for x in cite]
            c = [item for sublist in c for item in sublist]
            if len(c) != len(list(set(c))):
                seen = set()
                dupes = [x for x in c if x in seen or seen.add(x)]
                warns.append((i, "Duplicate citation key: %s" % ", ".join(dupes), re.search(dupes[0], l).span()))
    return warns


def check_multicite():
    warns = []
    for i, l in enumerate(tex_lines):
        cites = re.search("\\\\citeA?\\{[^\\}]+\\}\\s*\\\\citeA?\\{[^\\}]+\\}", l)
        if cites:
            warns.append((i, "Multiple \\cite commands, use multiple citation keys in one \\cite instead", cites.span()))
    return warns


def check_emptycite():
    warns = []
    for i, l in enumerate(tex_lines):
        cites = re.search("\\\\citeA?\\{\\s*\\}", l)
        if cites:
            warns.append((i, "Empty citation key", cites.span()))
    return warns

def check_conjunction_start():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        p = re.search("[\\.!?]\\s+(And|Or|But)[\\s,]", l.rstrip())
        if p:
            warns.append((i, "Starting a sentence with a conjunction is discouraged", p.span()))
        p = re.search("^(And|Or|But)[\\s,]", l.rstrip())
        if p:
            warns.append((i, "Starting a sentence with a conjunction is discouraged", p.span()))
    return warns


def check_brackets_space():
    warns = []
    for i, l in enumerate(tex_lines_clean):
        if in_code(i) or in_equation(i) or (len(l.strip()) > 0 and l.strip()[0] in ["\\", "%"]): continue
        masked = tex_lines_math_texttt_masked[i].rstrip()
        p = re.search("[^\\s\\{~\\\\]\\([^(s\\))]", masked)
        if p:
            warns.append((i, "There must be a space before an opening parenthesis", p.span()))
        p = re.search("\\(\\s", masked)
        if p:
            warns.append((i, "There must be no space after an opening parenthesis", p.span()))
        p = re.search("\\s\\)", masked)
        if p:
            warns.append((i, "There must be no space before a closing parenthesis", p.span()))
    return warns  


def check_acronym_capitalization():
    warns = []
    acronyms = set()
    acronym_first = {}
    for i, l in enumerate(tex_lines_clean):
        if in_code(i): continue
        for p in re.finditer("\\b[A-Z]{3,}\\b", l):
            acronym = p.group()
            pos = p.span()[0]
            if pos > 0 and l[pos - 1] == '\\':
                continue
            if acronym not in acronyms:
                acronyms.add(acronym)
                acronym_first[acronym] = i
    for i, l in enumerate(tex_lines_clean):
        if in_code(i): continue
        if "@" in l:
            continue
        for p in re.finditer("\\b[A-Za-z]{3,}\\b", l):
            found = p.group()
            if p.span()[0] > 0 and l[p.span()[0] - 1] == '\\':
                continue # probably a macro
            if l[:p.span()[0]].count("{") != l[:p.span()[0]].count("}"):
                continue # probably inside a reference or label
            canonical = found.upper()
            if found.endswith("s") and found[:-1].upper() in acronyms:
                found = found[:-1]
                canonical = found.upper()
            if canonical not in acronyms:
                continue
            if acronym_first[canonical] >= i:
                continue
            if found.islower():
                continue
            if not found.isupper():
                warns.append((i, "(Potential) acronym with wrong capitalization (first defined in Line %d)" % (acronym_first[canonical] + 1), p.span()))
    return warns  

def check_numeral():
    warns = []
    replace = [
        ("\\bthree\\b", "3"),
        ("\\bfour\\b", "4"),
        ("\\bfive\\b", "5"),
        ("\\bsix\\b", "6"),
        ("\\bseven\\b", "7"),
        ("\\beight\\b", "8"),
        ("\\bnine\\b", "9"),
        ("\\bten\\b", "10"),
        ("\\beleven\\b", "11"),
        ("\\btwelve\\b", "12")
    ]
    for i, l in enumerate(tex_lines):
        for r in replace:
            w = re.search(r[0], l)
            if w:
                warns.append((i, "Numeral \"%s\" should be replaced with \"%s\"" % (w.group(), r[1]), w.span()))
    return warns


def check_colors():
    warns = []
    cols = [
        "\\bred\\b",
        "\\bgreen\\b",
        "\\bblue\\b",
        "\\byellow\\b",
        "\\borange\\b",
        "\\bmagenta\\b",
        "\\bcyan\\b",
        "\\bbrown\\b",
        "\\bpink\\b"        
    ]
    modifiers = [
        "\\bdott?(ed)?\\b",
        "\\bdash(ed)?\\b",
        "\\bthick\\b",
        "\\bthin\\b",
        "\\bdash-?dotted\\b",
        "\\bhatch",
        "\\bcross",
        "\\bcheck",
        "\\bpattern"
    ]
    for i, l in enumerate(tex_lines):
        for c in cols:
            w = re.search(c, l)
            if w:
                prefix = l[:w.span()[0]].rstrip()
                # check for = or { in front of color
                if w.span()[0] > 0 and (l[w.span()[0] - 1] == "=" or l[w.span()[0] - 1] == "{"): continue
                if re.search(r"\\[A-Za-z@]+\*?(?:\{[^{}]*\})*\[[^\]]*$", prefix):
                    continue
                if prefix.endswith("[") or prefix.endswith(","):
                    continue
                # reduce false positives by looking for modifiers
                mod = False
                for m in modifiers:
                    if re.search(m, l):
                        mod = True
                        break
                if not mod:
                    warns.append((i, "Colors (\"%s\") without a modifier such as dashed/dotted/... should be avoided." % (w[0]), w.span()))
    return warns


def check_inconsistent_word_style():
    warns = []
    word_style = {}
    for i, l in enumerate(tex_lines_clean):
        styled = re.search(r"\\text([^\{]+)\{([^\}]+)\}", l)
        if styled and "newcommand" not in l:
            if styled[2] in word_style:
                if styled[1] != word_style[styled[2]][1][1]:
                    warns.append((i, "Word '%s' is styled inconsistently, used with \\text%s before at line %d" % (styled[2], word_style[styled[2]][1][1], word_style[styled[2]][0] + 1), styled.span()))
            else:
                word_style[styled[2]] = (i, styled)
    return warns


def check_missing_word_style():
    warns = []
    word_style = {}
    for i, l in enumerate(tex_lines_clean):
        styled = re.search(r"\\text([^\{]+)\{([^\}]+)\}", l)
        if styled:
            if len(styled[2]) <= 3: continue # reduce false positives for variables
            if styled[2] in word_style:
                word_style[styled[2]][2] += 1
            else:
                word_style[styled[2]] = [i, styled, 1]
                
    for i, l in enumerate(tex_lines_clean):
        if in_code(i): continue
        for s in word_style.keys():
            if word_style[s][2] == 1: continue # reduce false positives, e.g., when the word is emphasized once
            try:
                w = re.search("\\b%s\\b" % re.escape(s), l)
            except:
                continue
            if w:
                if w.span()[0] > 0 and l[w.span()[0] - 1] == "\\":
                    continue
                if w.span()[0] > 0 and l[w.span()[0] - 1] != "{":
                    warns.append((i, "Word '%s' used without a style, used with \\text%s before at line %d (and %d other location%s)" % (s, word_style[s][1][1], word_style[s][0] + 1, word_style[s][2], "s" if word_style[s][2] == 1 else ""), w.span()))
    return warns


def print_warnings(warn, output = True):
    warnings = 0
    sorted_warn = sorted(warn, key=lambda tup: tup[0][0])
    for cw in sorted_warn:
        w = cw[0]
        if w[0] != -1 and tex_lines[w[0]].strip().startswith("%"):
            continue
        if w[0] != -1 and in_comment(w[0]):
            continue
        if w[0] != -1 and in_code(w[0]) and cw[1] not in CODE_WARNING_EXCEPTIONS:
            continue

        if output: 
            print("\033[33mWarning %d\033[0m: " % (warnings + 1), end = "")
        warnings += 1
        if w[0] != -1:
            if output: print("Line %d: %s" % (w[0] + 1, w[1]), end = "")
        else:
            if output: print(w[1], end = "")
        
        if output:
            print("  \033[90m[%s]\033[0m" % cw[1], end = "")
            print("")

        if len(w) > 2:
            if output: print("    %s" % tex_lines[w[0]].replace("\t", " "))
            if output: print("    %s\033[33m%s\033[0m" % (" " * w[2][0], "^" * (w[2][1] - w[2][0])))
    return warnings


CATEGORY_GENERAL = 1
CATEGORY_TYPOGRAPHY = 2
CATEGORY_VISUAL = 4
CATEGORY_STYLE = 8
CATEGORY_REFERENCE = 16

checks = [
    (check_space_before_cite,           CATEGORY_TYPOGRAPHY, "cite-space"),
    (check_math_text_mix,               CATEGORY_TYPOGRAPHY, "math-text-mix"),
    (check_units,                       CATEGORY_TYPOGRAPHY, "units"),
    (check_figure_alignment,            CATEGORY_STYLE,      "figure-alignment"),
    (check_table_alignment,             CATEGORY_STYLE,      "table-alignment"),
    (check_listing_alignment,           CATEGORY_STYLE,      "listing-alignment"),
    (check_float_placement,             CATEGORY_STYLE,      "float-placement"),
    (check_figure_has_label,            CATEGORY_REFERENCE,  "figure-label"),
    (check_table_has_label,             CATEGORY_REFERENCE,  "table-label"),
    (check_listing_has_label,           CATEGORY_REFERENCE,  "listing-label"),
    (check_figure_has_caption,          CATEGORY_STYLE,      "figure-caption"),
    (check_table_has_caption,           CATEGORY_STYLE,      "table-caption"),
    (check_listing_has_caption,         CATEGORY_STYLE,      "listing-caption"),
    (check_no_resizebox_for_tables,     CATEGORY_STYLE,      "resize-table"),
    (check_weird_units,                 CATEGORY_STYLE,      "dimensions"),
    (check_figure_caption_label_order,  CATEGORY_REFERENCE,  "figure-caption-order"),
    (check_table_caption_label_order,   CATEGORY_REFERENCE,  "table-caption-order"),
    (check_listing_caption_label_order, CATEGORY_REFERENCE,  "listing-caption-order"),
    (check_todos,                       CATEGORY_GENERAL,    "todo"),
    (check_notes,                       CATEGORY_GENERAL,    "note"),
    (check_unused_macro,                CATEGORY_GENERAL,    "unused-macro"),
    (check_required_sections,           CATEGORY_GENERAL,    "required-sections"),
    (check_math_numbers,                CATEGORY_TYPOGRAPHY, "math-numbers"),
    (check_large_numbers_without_si,    CATEGORY_TYPOGRAPHY, "si"),
    (check_listing_in_correct_float,    CATEGORY_REFERENCE,  "listing-float"),
    (check_tabular_in_correct_float,    CATEGORY_REFERENCE,  "tabular-float"),
    (check_tikz_in_correct_float,       CATEGORY_REFERENCE,  "tikz-float"),
    (check_comment_has_space,           CATEGORY_TYPOGRAPHY, "comment-space"),
    (check_percent_without_siunix,      CATEGORY_TYPOGRAPHY, "percentage"),
    (check_short_form,                  CATEGORY_GENERAL,    "short-form"),
    (check_labels_referenced,           CATEGORY_REFERENCE,  "label-referenced"),
    (check_section_capitalization,      CATEGORY_VISUAL,     "capitalization"),
    (check_quotation,                   CATEGORY_TYPOGRAPHY, "quotes"),
    (check_hline_in_table,              CATEGORY_VISUAL,     "hline"),
    (check_duplicate_word,              CATEGORY_TYPOGRAPHY, "duplicate-word"),
    (check_space_before_punctuation,    CATEGORY_TYPOGRAPHY, "punctuation-space"),
    (check_headers_without_text,        CATEGORY_VISUAL,     "two-header"),
    (check_one_sentence_paragraphs,     CATEGORY_VISUAL,     "single-sentence"),
    (check_paragraph_length,            CATEGORY_VISUAL,     "paragraph-length"),
    (check_multiple_sentences_per_line, CATEGORY_GENERAL,    "multiple-sentences"),
    (check_unbalanced_brackets,         CATEGORY_TYPOGRAPHY, "unbalanced-brackets"),
    (check_and_or,                      CATEGORY_TYPOGRAPHY, "and-or"),
    (check_ellipsis,                    CATEGORY_TYPOGRAPHY, "ellipsis"),
    (check_etc,                         CATEGORY_STYLE,      "etc"),
    (check_punctuation_end_of_line,     CATEGORY_TYPOGRAPHY, "punctuation"),
    (check_footnote,                    CATEGORY_TYPOGRAPHY, "footnote"),
    (check_table_vertical_lines,        CATEGORY_VISUAL,     "vline"),
    (check_section_balance,             CATEGORY_VISUAL,     "section-balance"),
    (check_section_length,              CATEGORY_VISUAL,     "section-length"),
    (check_table_top_caption,           CATEGORY_STYLE,      "table-top-caption"),
    (check_will,                        CATEGORY_GENERAL,    "will"),
    (check_subsection_count,            CATEGORY_VISUAL,     "single-subsection"),
    (check_subsection_count_sanity,     CATEGORY_VISUAL,     "subsection-count"),
    (check_mixed_compact_and_item,      CATEGORY_VISUAL,     "mixed-compact"),
    (check_center_in_float,             CATEGORY_VISUAL,     "float-center"),
    (check_appendix,                    CATEGORY_STYLE,      "appendix"),
    (check_eqnarray,                    CATEGORY_VISUAL,     "eqnarray"),
    (check_deprecated,                  CATEGORY_STYLE,      "deprecated"),
    (check_package_conflict,            CATEGORY_STYLE,      "package-conflict"),
    (check_acm_pc,                      CATEGORY_STYLE,      "inclusion"),
    (check_cite_noun,                   CATEGORY_STYLE,      "cite-noun"),
    (check_cite_duplicate,              CATEGORY_REFERENCE,  "cite-duplicate"),
    (check_conjunction_start,           CATEGORY_STYLE,      "conjunction-start"),
    (check_brackets_space,              CATEGORY_TYPOGRAPHY, "bracket-spacing"),
    (check_acronym_capitalization,      CATEGORY_TYPOGRAPHY, "acronym-capitalization"),
    (check_numeral,                     CATEGORY_GENERAL,    "numeral"),
    (check_multicite,                   CATEGORY_STYLE,      "multiple-cites"),
    (check_emptycite,                   CATEGORY_REFERENCE,  "cite-empty"),
    (check_colors,                      CATEGORY_VISUAL,     "colors"),
    (check_inconsistent_word_style,     CATEGORY_TYPOGRAPHY, "inconsistent-textstyle"),
    (check_missing_word_style,          CATEGORY_TYPOGRAPHY, "missing-textstyle")
]

category_switches = [
    ("all",        CATEGORY_GENERAL | CATEGORY_REFERENCE | CATEGORY_STYLE | CATEGORY_TYPOGRAPHY | CATEGORY_VISUAL),
    ("general",    CATEGORY_GENERAL),
    ("reference",  CATEGORY_REFERENCE),
    ("style",      CATEGORY_STYLE),
    ("typography", CATEGORY_TYPOGRAPHY),
    ("visual",     CATEGORY_VISUAL)
]


def switch_exists(s):
    switches = [x[0] for x in category_switches] + [x[2] for x in checks]
    return s in switches


def add_categories(cat, new_cat):
    if type(new_cat) is str:
        full_cat = [x[0] for x in category_switches]
        if new_cat in full_cat:
            # full category, add everythingt that is not already there
            idx = full_cat.index(new_cat)
            new_cat = category_switches[idx][1]
        else:
            cat.add(new_cat)
    if type(new_cat) is int:
        for cats in checks:
            if new_cat & cats[1]:
                cat.add(cats[2])

        
def remove_categories(cat, rem_cat):
    if type(rem_cat) is str:
        full_cat = [x[0] for x in category_switches]
        if rem_cat in full_cat:
            # full category, add everythingt that is not already there
            idx = full_cat.index(rem_cat)
            rem_cat = category_switches[idx][1]
        else:
            if rem_cat in cat:
                cat.remove(rem_cat)
    if type(rem_cat) is int:
        for cats in checks:
            if (rem_cat & cats[1]) and cats[2] in cat:
                cat.remove(cats[2])


def main():

    nr_warnings = 0
    nr_suppressed = 0

    idx = 1
    has_rules = False
    exit_code = False
    
    # -x to exclude, -i to include
    used_categories = set()
    add_categories(used_categories, "all")
        
    while idx < len(sys.argv):
        arg = sys.argv[idx]
        if arg == "-x":
            if idx < len(sys.argv):
                if switch_exists(sys.argv[idx + 1]):
                    remove_categories(used_categories, sys.argv[idx + 1])
                    idx += 1
                    has_rules = True
                else:
                    print("Unknown switch '%s'" % sys.argv[idx + 1])
                    usage()
            else:
                print("Missing switch after -x")
                usage()

        if arg == "-i":
            if idx < len(sys.argv):
                if switch_exists(sys.argv[idx + 1]):
                    add_categories(used_categories, sys.argv[idx + 1])
                    idx += 1
                    has_rules = True
                else:
                    print("Unknown switch '%s'" % sys.argv[idx + 1])
                    usage()
            else:
                print("Missing switch after -i")
                usage()
        
        if arg == "--error":
            exit_code = True
        idx += 1

    if not has_rules:
        add_categories(used_categories, "all")

    for file in tex_files:
        next_file(file)
        print("Inspecting file \033[94m'%s'\033[0m" % file)
        
        preprocess()

        warnings = []
        suppressed = []
        for c in checks:
            add_warn = c[0]()
            if c[2] in used_categories:
                warnings += [(x, c[2]) for x in add_warn]
            else:
                suppressed += [(x, c[2]) for x in add_warn]

        nr_warnings += print_warnings(warnings)
        nr_suppressed += print_warnings(suppressed, output = False)

    print("")
    print("%d warnings printed; %d suppressed warnings" % (nr_warnings, nr_suppressed))
    if exit_code:
        sys.exit(1 if nr_warnings > 0 else 0)


if __name__ == "__main__":
    main()
