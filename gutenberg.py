#!/usr/bin/env python
"""Build a corpus from Project Gutenberg texts

    A quick and dirty script to build a corpus for
    truecaser from Project Gutenberg.

    Parameters
    ----------
    input_file : str
        The path to a file or directory that
        needs to be processed.

    output_file : str
        The path to the output file to be appended
        for each file added to the corpus

    --loop : bool
        If used, input_file is treated as a directory
        and each file in the directory is processed
        and saved to the output_file.

    --ignore-errors : bool
        If used gutenberg.py will ignore encoding 
        errors in input text. This option is recommended.
    Returns
    -------
    None
"""
import argparse
import os
import re

parser = argparse.ArgumentParser()
parser.add_argument("input_file")
parser.add_argument("output_file")
parser.add_argument("--loop", action="store_true")
parser.add_argument("--ignore-errors", action="store_true")

def load_in_text(gbook, error_option="strict"):
    reached_production_credits = False
    reached_end_of_preamble = False
    inside_brackets = False
    ends_with_page_num = re.compile(r".+ \d+\.?")
    starts_with_bad_char = re.compile(r'^[^A-Za-z"]')
    raw_lines = []

    with open(gbook, "r", encoding="utf-8", errors=error_option) as fh:
        for line in fh:
            line = line.rstrip()

            # If we reach the production credits, we're in the last part of the
            # Project Gutenberg preamble before the transcribed text. Until then
            # toss out everything.
            if not reached_production_credits:
                if line.startswith("Produced by"):
                    reached_production_credits = True
                continue

            # If we've reached the production line, we're near the end of
            # the preamble. Now check to see if we've reached a blank line.
            # Once we find a blank line, we're done with the preamble and need
            # to start checking the content of lines.
            if reached_production_credits:
                if not reached_end_of_preamble:
                    if not line:
                        reached_end_of_preamble = True
                    continue

            # If the line begins with a bracket it will often be in title-case,
            # so better to discard it. 
            if line.startswith("["):
                # If the bracketed text spans multiple lines, we'll want to 
                # make sure to delete all the lines.
                if not "]" in line:
                    inside_brackets = True
                continue

            # Check to see if we've reached the end of bracketed text
            if inside_brackets:
                if "]" in line:
                    inside_brackets = False
                continue

            # Now its time to throw out all the lines that are of no use or
            # aren't likely to be worth the extra processing effort. These fall
            # into a number of classes.
            if (
                # If the line is blank
                not line
                # or it starts with a character other than a letter,
                # which usually indicates nonstandard formatting or
                # even a line of non-alphabetic characters.
                or starts_with_bad_char.match(line)

                # or it is all caps
                or line == line.upper()
                # or it is an index line
                or ends_with_page_num.match(line)
                #or other_evils.search(line)
            ):
                continue

            # Reached end of transcribed text. No need to process the Project
            # Gutenberg end text and license, so break out of the loop.
            if (
                line.startswith("End of Project Gutenberg")
                or line.startswith("End of the Project Gutenberg EBook")
            ):
                break

            # If the line hasn't been rejected, add it to raw_lines
            raw_lines.append(line)

    return raw_lines


def secondary_processing(raw_lines):
    # Mush everything into one big string and remove any underscores
    # which are used to indicate italics in some Project Gutenberg texts.
    text = " ".join(raw_lines).replace("_", "")
    splitter = re.compile(r'((\.|!|\?)"?) ([^a-z])')
    starts_with_capital = re.compile(r"^[A-Z]")

    # Lines in Project Gutenberg ebooks are determined by length, but 
    # truecaser expects each line to be a full sentence. So we'll want
    # to split lines at sentence boundaries. Whenever we encounter a 
    # period, question mark, or exclaimation mark, optionally followed
    # by double quotes we split the line as long as it's not followed
    # by a lowercase letter that might indicate speech, like '"This is
    # only part of a sentence!" he proclaimed.'
    split_text = splitter.split(text)
    lines = []
    to_join = []
    lines_fixed = []

    need_punctuation = True
    find_punctuation = re.compile(r"^[\.\?!]")

    # Having split up our lines, we'll need to rejoin them.
    for i in split_text:
        # Collect every segment until we find sentence-ending punctuation.
        if need_punctuation:
            if find_punctuation.match(i):
                need_punctuation = False
            to_join.append(i)
        # Once we've reached the end of the sentence, join the parts
        # together, add the line to the lines list and clear to_join
        # for the next set of segment pieces.
        else:
            lines.append("".join(to_join))
            to_join = []
            need_punctuation = True

    lines.append("".join(to_join).strip())

    for line in lines:
        # If the line is too short or it doesn't start with a capital letter,
        # there's a good chance it's not a real sentence, so toss it. 
        if len(line) < 20 or not starts_with_capital.match(line):
            continue
        # Otherwise, time to start processing.
        else:
            # Split the sentence into tokens.
            tokens = line.split()
            # For each token in tokens, return the token unaltered if it's not
            # all uppercase. Otherwise return the token in lowercase if it's
            # not the first token in the list. If it is the first, return it
            # with the first letter capitalized.
            tokens_fixed = [x 
                            if x != x.upper() 
                            else x.lower() 
                                    if x == x.upper() and tokens.index(x) > 0 
                                    else x.title() 
                            for x in tokens]
            # Convert the list of tokens back into a single string.
            lines_fixed.append(" ".join(tokens_fixed))

    # Return fixed strings as one long string with one sentence per line.
    return "\n".join(lines_fixed)


def append_to_output_file(output, output_file):
    with open(output_file, 'a', encoding="utf-8") as fh:
        fh.write(output)


def gutenloop(input_dir, output_file, error_option):
    for file_ in os.listdir(input_dir):
        file_path = os.path.join(input_dir, file_)
        main(file_path, output_file, error_option)


def main(input_file, output_file, error_option):
    raw_lines = load_in_text(input_file, error_option)
    corpus_part = secondary_processing(raw_lines)
    append_to_output_file(corpus_part, output_file)


if __name__ == "__main__":
    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file
    loop = args.loop

    error_option = "strict"

    if args.ignore_errors:
        error_option = "ignore"

    if loop:
        gutenloop(input_file, output_file, error_option)
    else:
        main(input_file, output_file, error_option)
