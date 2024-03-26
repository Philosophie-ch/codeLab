#!/usr/bin/env python3

from typing import List
from titlecase import titlecase


def title_casing(title: str) -> str:
    """
    Convert a string to title case. Forces the `titlecase` method by converting the string to lowercase first.
    """
    lower_title = title.lower()
    return titlecase(lower_title)


def main(title_list: List[str]) -> List[str]:
    """
    Loop over the main functionality
    """

    return [title_casing(title) for title in title_list]


def cli() -> None:

    import argparse

    parser = argparse.ArgumentParser(description="Convert a list of strings to title case.")

    parser.add_argument("file", type=argparse.FileType("r"), help="File containing a list of strings to convert to title case. Each line of the file must be a string that we want to titlecase.")

    args = parser.parse_args()

    title_list = [line.strip() for line in args.file]

    for title in main(title_list):
        print(title)


if __name__ == "__main__":
    cli()