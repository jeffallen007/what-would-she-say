# This file takes an input file and generates character lines for a specific character.

def generate_character_lines(input_file, character_name, output_file):
    """
    Reads a CSV file containing character dialogues, filters for a specific character,
    and writes their lines to an output file.

    :param input_file: Path to the input CSV file containing character dialogues.
    :param character_name: Name of the character whose lines are to be extracted.
    :param output_file: Path to the output file where the character's lines will be saved.
    """
    import pandas as pd

    # Read the input CSV file
    df = pd.read_csv(input_file)

    # Filter for the specified character's lines
    character_lines = df[df["raw_character_text"] == character_name]["spoken_words"].dropna()

    # Write the character's lines to the output file
    character_lines.to_csv(output_file, sep='\t', index=False)

# Example usage
input_file = "source_files/simpsons_dataset.csv"
character_name = "Homer Simpson"
output_file = "source_files/homer_lines.txt"
generate_character_lines(input_file, character_name, output_file)
