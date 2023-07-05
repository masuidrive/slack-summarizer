""" Utility functions for the project. """

import re
import time
import emoji


def retry(func, max_retries=5, sleep_time=10, exception=Exception):
    """ A decorator function that retries the function call if it fails.

    Args:
        func (callable): The function to be wrapped.
        max_retries (int, optional): The maximum number of retries. Defaults to 5.
        sleep_time (int, optional): The sleep time in seconds between retries. Defaults to 10.
        exception (Exception, optional): The expected exception class to catch and retry if raised. Defaults to Exception.

    Returns:
        result of func call.

    Examples:
        result = self.retry(lambda: slack_client.conversations_list(types="public_channel", exclude_archived=True, limit=1000))
    """

    for i in range(max_retries):
        try:
            result = func()
            return result
        except exception as error:
            if i == max_retries - 1:
                raise error
            time.sleep(sleep_time)
    return None


def sort_by_numeric_prefix(lst, get_key=lambda x: x):
    """
    Sorts the list based on whether the element has a numeric prefix.
    If an element has a numeric prefix, it is sorted in ascending order based on the numeric value.
    If an element does not have a numeric prefix, it is sorted in ascending order based on the alphabetical order of the string.
    
    Args:
        lst: A list of strings
        get_key: A function that takes a string and returns a key to sort on.
                 Default is identity function that returns the string itself.
    
    Returns:
        A sorted list of strings

    Example:
        >>> lst = [{"name":"a"}, {"name":"1abc"}, {"name":"Z"}, {"name":"う"}, {"name":"あ"}, {"name":"14:A"}]
        >>> sort_by_numeric_prefix(lst, get_key=lambda x: x["name"])
        [{'name': '14:A'}, {'name': '1abc'}, {'name': 'Z'}, {'name': 'a'}, {'name': 'あ'}, {'name': 'う'}]

    """
    digits_list = [s for s in lst if re.match(r'^(\d+)', get_key(s))]
    string_list = [s for s in lst if re.match(r'^\D', get_key(s))]

    def numkey(n: str):
        match = re.match(r'^(\d+)', get_key(n))
        return int(match.group(1))

    return sorted(digits_list, key=numkey) + sorted(string_list, key=get_key)


def remove_emoji(text: str) -> str:
    """
    Remove emojis from the given text.

    Args:
        text (str): A string containing the text to remove custom emojis from.

    Returns:
        str: The input text with custom emojis removed.

    Example:
        >>> text = "Hello, world! :smile: :wave:"
        >>> remove_custom_emoji(text)
        'Hello, world!  '
    """
    # Remove Unicode emojis
    text = emoji.replace_emoji(text, replace='')

    # Remove Slack custom emojis
    custom_pattern = r":[-_a-zA-Z0-9]+?:"
    text = re.sub(custom_pattern, "", text)
    return text
