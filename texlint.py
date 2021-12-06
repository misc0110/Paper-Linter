import re
import sys


def usage():
    print("%s <file.tex> [-x <excluded-switch1>] [-i <included-switch1>] [-i/x <switch n, evaluated in order of specification>]" % sys.argv[0])
    sys.exit(1)

if len(sys.argv) < 2:
    usage()

try:
    tex = open(sys.argv[1]).read()
except:
    print("Could not open '%s'" % sys.argv[1])
    sys.exit(1)

tex_lines = tex.split("\n")
tex_lines_clean = tex.split("\n")
in_env = {}
envs = {}


def preprocess():
    env = list(set(re.findall("\\\\begin\{(\\w+)\}", tex)))
    for e in env:
        in_env[e] = []
        envs[e] = []
        current_start = -1
        for i, l in enumerate(tex_lines):
            if re.search("\\\\begin\{%s" % e, l):
                in_env[e].append(True)
                current_start = i
            elif re.search("\\\\end\{%s" % e, l):
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


def in_any_env(line):
    for e in in_env:
        if in_env[e][line]:
            return True
    return False


def in_any_float(line):
    floats = ["figure", "listing", "table"]
    for f in floats:
        if f in in_env and in_env[f][line]:
            return True
    return False

def in_code(line):
    if "lstlisting" in in_env:
        return in_env["lstlisting"][line]
    return False

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
        b = re.search("\\\\begin\{%s\}" % env, l)
        if b:
            if not re.search("%s}\[[^\]]*[htbH][^\]]*\]" % env, l):
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
            b = re.search("\\\\label\{", tex_lines[i])
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
            b = re.search("\\\\caption\{", tex_lines[i])
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
            b = re.search("\\\\caption\{", tex_lines[i])
            if b:
                caption = i
            b = re.search("\\\\label\{", tex_lines[i])
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
            b = re.search("\\\\resizebox\{", tex_lines[i])
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
    for i, l in enumerate(tex_lines):
        if "TODO" in l:
            warns.append((i, "TODO found", (l.index("TODO"), l.index("TODO") + 4)))
    return warns


def check_notes():
    warns = []
    for i, l in enumerate(tex_lines):
        if "\\note" in l:
            warns.append((i, "\\note found", (l.index("\\note"), l.index("\\note") + 5)))
        if "\\todo" in l:
            warns.append((i, "\\todo found", (l.index("\\todo"), l.index("\\todo") + 5)))
    return warns


def check_math_numbers():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search("\\$\\d+\\$", tex_lines[i]) 
        if n and not in_any_float(i):
            warns.append((i, "Number in math mode, consider using siunit instead", n.span()))
    return warns


def check_large_numbers_without_si():
    warns = []
    for i, l in enumerate(tex_lines):
        n = re.search("[\\s\(]\\d{5,}[\\s\),\.]", tex_lines[i]) 
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
    for i, l in enumerate(tex_lines):
        n = re.search("[^`%]\\w+'[^s' ,.!?\-0-9]", l)
        if n:
            warns.append((i, "Contracted form used", n.span()))
    return warns


def check_labels_referenced():
    warns = []
    labels = re.findall("\\\\label\{([^\\}]+)\}", tex)
    for lab in labels:
        found = False
        for i, l in enumerate(tex_lines):
            if ("ref{%s}" % lab) in l:
                found = True
                break
        if not found:
            warns.append((-1, "Label %s is not referenced" % lab))
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
    for i, l in enumerate(tex_lines):
        ws = re.search("\"\\w+", l)
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
        if p:
            warns.append((i, "Multiple sentences in one line", p.span()))
    return warns


def check_unbalanced_brackets():
    warns = []
    for i, l in enumerate(tex_lines):
        if l.count("(") != l.count(")") and not in_code(i):
            first = min(l.index("(") if l.count("(") > 0 else len(l), l.index(")") if l.count(")") > 0 else len(l))
            last = max(l.rindex("(") if l.count("(") > 0 else len(l), l.rindex(")") if l.count(")") > 0 else len(l))
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
    for i, l in enumerate(tex_lines):
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
            it = re.search("\\\\begin\{enumerate\}", l)
            if it:
                warns.append((i, "compactenum mixed with enumerate", it.span()))
    if "\\begin{compactitem}" in tex:
        for i, l in enumerate(tex_lines):
            it = re.search("\\\\begin\{itemize\}", l)
            if it:
                warns.append((i, "compactitem mixed with itemize", it.span()))
    return warns


def check_center_in_float():
    warns = []
    if "center" in envs:
        for c in envs["center"]:
            if in_any_float(c[0]):
                warns.append((c[0], "Use \\centering instead of \\begin{center} inside floats", re.search("\\\\begin\{center\}", tex_lines[c[0]]).span()))
    return warns


def check_appendix():
    warns = []
    for i, l in enumerate(tex_lines):
        ap = re.search("\\\\begin\{appendix\}", l)
        if ap:
            warns.append((i, "Use \\appendix instead of \\begin{appendix}", ap.span()))
    return warns


def check_eqnarray():
    warns = []
    for i, l in enumerate(tex_lines):
        ap = re.search("\\\\begin\{eqnarray\}", l)
        if ap:
            warns.append((i, "Use \\begin{align} instead of \\begin{eqnarray}", ap.span()))
    return warns


def print_warnings(warn, output = True):
    warnings = 0
    sorted_warn = sorted(warn, key=lambda tup: tup[0])
    for w in sorted_warn:
        if w[0] != -1 and tex_lines[w[0]].strip().startswith("%"):
            continue

        if output: print("\033[33mWarning %d\033[0m: " % (warnings + 1), end = "")
        warnings += 1
        if w[0] != -1:
            if output: print("Line %d: %s" % (w[0] + 1, w[1]))
        else:
            if output: print(w[1])
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
    (check_figure_alignment,            CATEGORY_STYLE,      "figure-alignment"),
    (check_table_alignment,             CATEGORY_STYLE,      "table-alignment"),
    (check_listing_alignment,           CATEGORY_STYLE,      "listing-alignment"),
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
    (check_space_before_punctuation,    CATEGORY_TYPOGRAPHY, "punctuation-space"),
    (check_headers_without_text,        CATEGORY_VISUAL,     "two-header"),
    (check_one_sentence_paragraphs,     CATEGORY_VISUAL,     "single-sentence"),
    (check_multiple_sentences_per_line, CATEGORY_GENERAL,    "multiple-sentences"),
    (check_unbalanced_brackets,         CATEGORY_TYPOGRAPHY, "unbalanced-brackets"),
    (check_and_or,                      CATEGORY_TYPOGRAPHY, "and-or"),
    (check_ellipsis,                    CATEGORY_TYPOGRAPHY, "ellipsis"),
    (check_etc,                         CATEGORY_STYLE,      "etc"),
    (check_punctuation_end_of_line,     CATEGORY_TYPOGRAPHY, "punctuation"),
    (check_footnote,                    CATEGORY_TYPOGRAPHY, "footnote"),
    (check_table_vertical_lines,        CATEGORY_VISUAL,     "vline"),
    (check_table_top_caption,           CATEGORY_STYLE,      "table-top-caption"),
    (check_will,                        CATEGORY_GENERAL,    "will"),
    (check_subsection_count,            CATEGORY_VISUAL,     "single-subsection"),
    (check_mixed_compact_and_item,      CATEGORY_VISUAL,     "mixed-compact"),
    (check_center_in_float,             CATEGORY_VISUAL,     "float-center"),
    (check_appendix,                    CATEGORY_STYLE,      "appendix"),
    (check_eqnarray,                    CATEGORY_VISUAL,     "eqnarray")
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
    preprocess()

    # -x to exclude, -i to include
    used_categories = set()

    idx = 1
    has_rules = False
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
        idx += 1

    if not has_rules:
        add_categories(used_categories, "all")

    warnings = []
    suppressed = []
    for c in checks:
        add_warn = c[0]()
        if c[2] in used_categories:
            warnings += add_warn
        else:
            suppressed += add_warn

    nr_warnings = print_warnings(warnings)
    nr_suppressed = print_warnings(suppressed, output = False)

    print("")
    print("%d warnings printed; %d suppressed warnings" % (nr_warnings, nr_suppressed))


if __name__ == "__main__":
    main()

