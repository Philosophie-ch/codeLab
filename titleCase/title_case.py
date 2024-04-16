#!/usr/bin/env python3

from typing import Generator, List
from titlecase import titlecase


def title_casing(title: str) -> str:
    """
    Convert a string to title case. Forces the `titlecase` method by converting the string to lowercase first.
    """
    lower_title = title.lower()
    return titlecase(lower_title)


def main(title_list: List[str]) -> Generator[str, None, None]:
    """
    Loop over the main functionality. Returns a generator of title cased strings, as it's more memory-efficient than returning a list.
    """

    return (title_casing(title) for title in title_list)


def cli() -> None:

    # CLI inputs
    import argparse

    parser = argparse.ArgumentParser(description="Convert a list of strings to title case.")

    parser.add_argument("file", type=argparse.FileType("r"), help="File containing a list of strings to convert to title case. Each line of the file must be a string that we want to titlecase.")

    args = parser.parse_args()


    # Main
    titles = main(args.file)


    # Secondary effects
    for title in titles:
        print(title, end="")
    print()


if __name__ == "__main__":
    cli()