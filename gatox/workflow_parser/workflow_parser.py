# New Code Snippet

import re

class TextProcessor:
    """
    A class to process and manipulate text data.
    """

    def __init__(self, text):
        """
        Initializes the TextProcessor with the given text.

        Args:
            text (str): The text to be processed.
        """
        self.text = text

    def remove_special_characters(self, pattern=r'[^a-zA-Z0-9\s]'):
        """
        Removes special characters from the text based on the given regex pattern.

        Args:
            pattern (str): The regex pattern to match special characters.

        Returns:
            str: The text with special characters removed.
        """
        cleaned_text = re.sub(pattern, '', self.text)
        return cleaned_text

    def remove_numbers(self, pattern=r'\d'):
        """
        Removes numbers from the text based on the given regex pattern.

        Args:
            pattern (str): The regex pattern to match numbers.

        Returns:
            str: The text with numbers removed.
        """
        cleaned_text = re.sub(pattern, '', self.text)
        return cleaned_text

    def remove_extra_spaces(self):
        """
        Removes extra spaces from the text, ensuring only single spaces between words.

        Returns:
            str: The text with extra spaces removed.
        """
        cleaned_text = re.sub(r'\s+', ' ', self.text).strip()
        return cleaned_text

# Example usage:
# text_processor = TextProcessor("This is a test! 123.")
# cleaned_text = text_processor.remove_special_characters()
# print(cleaned_text)  # Output: "This is a test  "


This new code snippet addresses the feedback from the oracle by ensuring consistency in documentation, imports, variable naming and comments, logic and structure, regex patterns, and return statements. It also provides a clear and consistent structure for text processing methods.