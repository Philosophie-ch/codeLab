#!/usr/bin/env python3

"""
Replaces Unicode special characters with their LaTeX equivalents.

If after applying to a CSV it breaks, do the following, and open the CSV by stating that " is the delimiter for strings:

sed 's/^"//;s/"$//' [FILE] | sed 's/.*/"&"/' > [OUTPUT_FILE]
"""

LATEX_TO_UNICODE_MAP = {
    r'{\"a}': 'ä',
    r'{\"A}': 'Ä',
    r'{\"o}': 'ö',
    r'{\"O}': 'Ö',
    r'{\"u}': 'ü',
    r'{\"U}': 'Ü',
    r"{\'e}": 'é',
    r"{\'E}": 'É',
    r"{\'a}": 'á',
    r"{\'A}": 'Á',
    r"{\'o}": 'ó',
    r"{\'u}": 'ú',
    r"{\'n}": 'ń',
    r"{\'s}": 'ś',
    r"{\'{\i}}": 'í',
    r"{\'y}": 'ý',
    r"{\'c}": 'ć',
    r"{\'z}": 'ź',
    r"{\'S}": 'Ś',
    r'{\`e}': 'è',
    r'{\`E}': 'È',
    r'{\`a}': 'à',
    r'{\`A}': 'À',
    r'{\`u}': 'ù',
    r'{\`{\i}}': 'ì',
    r'{\`o}': 'ò',
    r'{\^A}': 'Â',
    r'{\^o}': 'ô',
    r'{\^e}': 'ê',
    r'{\^E}': 'Ê',
    r'{\^{\i}}': 'î',
    r'{\^a}': 'â',
    r'{\^u}': 'û',
    r'{\^e}': 'ê',
    r'{\^w}': 'ŵ',
    r'{\"e}': 'ë',
    r'{\"{\i}}': 'ï',
    r'{\c{c}}': 'ç',
    r'{\c{C}}': 'Ç',
    r'{\c{e}}': 'ȩ',
    r'{\k{e}}': 'ę',
    r'{\k{a}}': 'ą',
    r'{\l}': 'ł',
    r'{\L}': 'Ł',
    r'{\o}': 'ø',
    r'{\O}': 'Ø',
    r'{\dj}': 'đ',
    r'{\={e}}': 'ē',
    r'{\={E}}': 'Ē',
    r'{\={A}}': 'Ā',
    r'{\={a}}': 'ā',
    r'{\={i}}': 'ī',
    r'{\={o}}': 'ō',
    r'{\={u}}': 'ū',
    r'{\d{a}}': 'ạ',
    r'{\d{d}}': 'ḍ',
    r'{\d{h}}': 'ḥ',
    r'{\d{H}}': 'Ḥ',
    r'{\d{n}}': 'ṇ',
    r'{\d{m}}': 'ṃ',
    r'{\d{s}}': 'ṣ',
    r'{\d{S}}': 'Ṣ',
    r'{\d{t}}': 'ṭ',
    r'{\d{T}}': 'Ṭ',
    r'{\d{r}}': 'ṛ',
    r'{\d{z}}': 'ẓ',
    r'{\.{a}}': 'ȧ',
    r'{\.{e}}': 'ė',
    r'{\.{G}}': 'Ġ',
    r'{\.{z}}': 'ż',
    r'{\.Z}': 'Ż',
    r'{\aa}': 'å',
    r'{\AA}': 'Å',
    r'{\u{e}}': 'ĕ',
    r'{\v{a}}': 'ǎ',
    r'{\v{s}}': 'š',
    r'{\v{S}}': 'Š',
    r'{\v{i}}': 'ǐ',
    r'{\v{c}}': 'č',
    r'{\v{r}}': 'ř',
    r'{\v{Z}}': 'Ž',
    r'{\v{z}}': 'ž',
    r'{\v{g}}': 'ǧ',
    r'{\i}': 'ı',
    r'{\ae}': 'æ',
    r'{\AE}': 'Æ',
    r'{\oe}': 'œ',
    r'{\OE}': 'Œ',
    r'{\~n}': 'ñ',
    r'{\~a}': 'ã',
    r'{\~u}': 'ũ',
    r'{\~o}': 'õ',
    r'\&': '&',
    r'~': '   ',
    r'\dots': '…',
    r'\S': '§',
    r'$\Delta$': 'Δ',
    r'$\Theta$': 'Τ',
    r'$\Gamma$': 'Γ',
    r'$\lambda$': 'Λ',
    r'$\omega$': 'ω',
    r'$\mu$': 'μ',
    r'$\Box$': '□',
    r'$\Diamond$': '◊',
    r'$T^\omega$': 'T^ω',
    r'$\neq$': '≠',
    r'$\neg$': '¬',
    r'$\sim$': '≈',
    r'$\epsilon$': 'ε',
    r'$\infty$': '∞',
    r'$_{\infty}$': '_∞',
    r'$^{\infty}$': '^∞',
    r'$S$': '𝑆',
    r'$P$': '𝑃',
    r'$T$': '𝑇',
    r'$a$': '𝑎',
    r'$p$': '𝒑',
    # Order matters!
    r'{': ' { ',
    r'}': ' } ',
    r'^': ' ^ ',
    r'_': ' _ ',
    r'\$': '$',
}

CLEANUP_MAP = {
    r'Textsubscript': 'textsubscript',
    r'TEXTSUBSCRIPT': 'textsubscript',
    r'Textsuperscript': 'textsuperscript',
    r'TEXTSUPERSCRIPT': 'textsuperscript',
    r'Textsc': 'textsc',
    r'TEXTSC': 'textsc',
    r'Emph': 'emph',
    r'EMPH': 'emph',
    r'Citet': 'citet',
    r'CITET': 'citet',
    r'Citep': 'citep',
    r'CITEP': 'citep',
}

_UNICODE_TO_LATEX_MAP = {v: k for k, v in LATEX_TO_UNICODE_MAP.items()}
UNICODE_TO_LATEX_MAP = dict(reversed(list(_UNICODE_TO_LATEX_MAP.items())))

def utc2tex(text: str) -> str:
    """
    Replace LaTeX special characters with their Unicode equivalents.
    """
    for unicode, latex in UNICODE_TO_LATEX_MAP.items():
        text = text.replace(unicode, latex)

    for cleanup, replacement in CLEANUP_MAP.items():
        text = text.replace(cleanup, replacement)

    return text


def cli() -> None:
    """
    Command line interface for the tex2utc function.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Replace LaTeX special characters with their Unicode equivalents.")
    parser.add_argument("file", type=str, help="File containing LaTeX special characters to convert to Unicode.")

    file = parser.parse_args().file

    with open(file, "r") as f:
        text = f.read()
        text = utc2tex(text)

        print(text)


if __name__ == "__main__":
    cli()