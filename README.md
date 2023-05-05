# LaTeX Paper Linter

This script checks for common mistakes in LaTeX source files of scientific papers. 

## Usage

    python3 paperlint.py <file.tex/path> [-i/x <include/exclude switch>] [--error]

Provide either a single .tex file to check or a path to recursively check all .tex files in that directory!
By default, all rules are used for checking the document.
The switches can be configured with the `-x` and `-i` parameters to exclude and include entire categories of rules or single rules. 
The include/exclude switches are evaluated in the order they are specified. 
For example, `-i typography` only activates the typography rules, whereas `-i all -x typography -i cite-space` enables all rules without the typography rules, but enables the `cite-space` rule from the typography category. 

If `--error` is provided, the tool exits with error code 1 if there are warnings.

## Warnings

Warnings are grouped in five different categories:

* General
* Typography
* Visual
* Style
* References

### General
This category includes general mistakes and discouraged things (switch `general`).

#### TODOs
* **Description**: Warns if the string "TODO" appears in the paper
* **Switch**: `todo`

#### Notes
* **Description**: Warns if there are `\note` or `\todo` notes in the paper
* **Switch**: `note`

#### Multiple Sentences per Line
* **Description**: Warns if there are multiple sentences per line
* **Switch**: `multiple-sentences`

#### Will Future
* **Description**: Warns if there are sentences with "will" future
* **Switch**: `will`

#### Short Forms
* **Description**: Warns if short forms, such as "can't", "shouldn't", etc., are used
* **Switch**: `short-form`

#### Numerals
* **Description**: Warns if numbers 3 to 12 are written as words instead of numbers
* **Switch**: `numeral`


### Typography
This category includes typography-related issues, such as wrong punctuation (switch `typography`).

#### No Space before Citation
* **Description**: Warns if there is no space before a `\cite` command
* **Switch**: `cite-space`

#### Numbers in math Environment
* **Description**: Warns if the math environment is used purely to format numbers
* **Switch**: `math-numbers`

#### Large Numbers without siunit
* **Description**: Warns if large numbers are not formatted with the `sinuit` package
* **Switch**: `si`

#### Percentage without siunit
* **Description**: Warns if percentages are not formatted with the `siunit` package
* **Switch**: `percentage`

#### Wrong Quotation Marks
* **Description**: Warns if the wrong quotation marks (") are used
* **Switch**: `quotes`

#### Space before Punctuation
* **Description**: Warns if there is a space before a punctuation character
* **Switch**: `punctuation-space`

#### Unbalanced Brackets
* **Description**: Warns if the number of opening and closing brackets per line does not match
* **Switch**: `unbalanced-brackets`

#### Usage of and/or
* **Description**: Warns if "and/or" is used
* **Switch**: `and-or`

#### Ellipsis with ...
* **Description**: Warns if an ellipsis with three dots ("...") is used
* **Switch**: `ellipsis`

#### Footnote before Period
* **Description**: Warns if a footnote is before the period
* **Switch**: `footnote`

#### No Punctuation Mark at End of Line
* **Description**: Warns if a line does not end with a punctuation mark
* **Switch**: `punctuation`

#### No Space before Comment
* **Description**: Warns if there is no space before a comment
* **Switch**: `comment-space`

#### Brackets with Wrong Spacing
* **Description**: Warns if the spacing for brackets are wrong, i.e., if there is no space before an opening bracket, a space after an opening bracket, or a space before a closing bracket
* **Switch**: `bracket-spacing`

#### Acronym Capitalization
* **Description**: Warns if a (potential) acronym is not written in upper case
* **Switch**: `acronym-capitalization`


### Visual
This category includes warning regarding code that is visually not optimal and can be improved to make the paper look better (switch `visual`).

#### hlines in Tables
* **Description**: Warns if `\hline` is used in tables instead of `\toprule`, `\midrule`, and `\bottomrule`
* **Switch**: `hline`

#### No Text between Two Headers
* **Description**: Warns if there are two section headers without text in between
* **Switch**: `two-header`

#### Single Sentence Paragraphs
* **Description**: Warns if a paragraph consists of only a single sentence
* **Switch**: `single-sentence`

#### Tables with Vertical Lines
* **Description**: Warns if vertical lines are used in tables
* **Switch**: `vline`

#### Single subsection in a Section
* **Description**: Warns if a section has only one explicit subsection
* **Switch**: `single-subsection`

#### Mixed Compact and Regular Lists
* **Description**: Warns if both `compactitem` and `itemize` (or `compactenum` and `enumerate`) are used
* **Switch**: `mixed-compact`

#### Center instead of \centering in Floats
* **Description**: Warns if float contents are centered with the `center` environment instead of `\centering`
* **Switch**: `float-center`

#### Usage of eqnarray instead of align Environment
* **Description**: Warns if the `eqnarray` environment is used instead of the `align` environment
* **Switch**: `eqnarray`

#### Section-Title Capitalization
* **Description**: Warns if the capitalization for section titles is wrong
* **Switch**: `capitalization`

#### Colors without Modifiers
* **Description**: Warns if a color is used without an additional (non-color) modifier such as "dashed/dotted/..."
* **Switch**: `colors`


### Style
This category includes warning of things that are discouraged or wrong for the style of an academic paper (switch `style`).

#### Wrong Appendix
* **Description**: Warns if the `appendix` environment is used instead of `\appendix`
* **Switch**: `appendix`

#### Non-generic Dimensions
* **Description**: Warns if dimension macros are used that do not always work, such as \linewidth or \textwidth
* **Switch**: `dimensions`

#### Usage of "etc"
* **Description**: Warns if "etc" is used
* **Switch**: `etc`

#### Enlarged Tables
* **Description**: Warns if `resizebox` (instead of `adjustbox`) is used for tables
* **Switch**: `resize-table`

#### Caption above Tables
* **Description**: Warns if the caption for a table is not above the table
* **Switch**: `table-top-caption`

#### Figure Alignment
* **Description**: Warns if a figure has no explicit alignment
* **Switch**: `figure-alignment`

#### Table Alignment
* **Description**: Warns if a table has no explicit alignment
* **Switch**: `table-alignment`

#### Listing Alignment
* **Description**: Warns if a listing has no explicit alignment
* **Switch**: `listing-alignment`

#### Non-inclusive Wording
* **Description**: Warns if non-inclusive terms are used (based on the [ACM Guidelines](https://www.acm.org/diversity-inclusion/words-matter))
* **Switch**: `inclusion`

#### Citation as Noun
* **Description**: Warns if a citation is used as a noun
* **Switch**: `cite-noun`

#### Multiple cite Commands
* **Description**: Warns if multiple `\cite` commands are used instead of having multiple citation keys inside one `\cite`
* **Switch**: `multiple-cites`

#### Sentence starting with a Conjunction 
* **Description**: Warns if a sentence starts with a conjunction ("And", "But", "Or")
* **Switch**: `conjunction-start`


### References
This category includes warnings for everything related to (cross-)references (switch `references`).

#### Figure without Label
* **Description**: Warns if a figure has no label
* **Switch**: `figure-label`

#### Table without Label
* **Description**: Warns if a table has no label
* **Switch**: `table-label`

#### Listing without Label
* **Description**: Warns if a listing has no label
* **Switch**: `listing-label`

#### Switched Order of Label and Caption in Figure
* **Description**: Warns if the label is defined before the caption inside a figure
* **Switch**: `figure-caption-order`

#### Switched Order of Label and Caption in Table
* **Description**: Warns if the label is defined before the caption inside a table
* **Switch**: `table-caption-order`

#### Switched Order of Label and Caption in Listing
* **Description**: Warns if the label is defined before the caption inside a listing
* **Switch**: `listing-caption-order`

#### Non-referenced Labels
* **Description**: Warns if there is a label defined that is never referenced
* **Switch**: `label-referenced`

#### Tabular not in Table Environment
* **Description**: Warns if a `tabular` environment is not within the `table` float
* **Switch**: `tabular-float`

#### TikZ not in Figure Environment
* **Description**: Warns if a `tikzpicture` environment is not within the `figure` float
* **Switch**: `tikz-float`

#### Code Listing not in Listing Environment
* **Description**: Warns if an `lstlisting` environment is not within the `listing` float
* **Switch**: `listing-float`

#### Duplicate Keys in Citations
* **Description**: Warns if a `cite` command has duplicate entries
* **Switch**: `cite-duplicate`
