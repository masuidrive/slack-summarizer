#!/usr/bin/env python3
"""
https://github.com/masuidrive/slack-summarizer
  by [masuidrive](https://twitter.com/masuidrive) @ [Bloom&Co., Inc.](https://www.bloom-and-co.com/)
  2023- [APACHE LICENSE, 2.0](https://www.apache.org/licenses/LICENSE-2.0)
"""
import os
import re
import sys
from datetime import datetime, timedelta
import pytz
import openai
from slack_sdk.errors import SlackApiError
from lib.slack import SlackClient
from lib.utils import remove_emoji, retry


def summarize(text: str, language: str = "Japanese"):
    """
    Summarize a chat log in bullet points, in the specified language.

    Args:
        text (str): The chat log to summarize, in the format "Speaker: Message" separated by line breaks.
        language (str, optional): The language to use for the summary. Defaults to "Japanese".

    Returns:
        str: The summarized chat log in bullet point format.

    Examples:
        >>> summarize("Alice: Hi\nBob: Hello\nAlice: How are you?\nBob: I'm doing well, thanks.")
        '- Alice greeted Bob.\n- Bob responded with a greeting.\n- Alice asked how Bob was doing.\n- Bob replied that he was doing well.'
    """
    response = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        temperature=TEMPERATURE,
        messages=[{
            "role":
            "system",
            "content":
            "\n".join([
                'The chat log format consists of one line per message in the format "Speaker: Message".',
                "The `\\n` within the message represents a line break."
                f'The user understands {language} only.',
                f'So, The assistant need to speak in {language}.',
            ])
        }, {
            "role":
            "user",
            "content":
            "\n".join([
                f"Please meaning summarize the following chat log to flat bullet list in {language}.",
                "It isn't line by line summary.",
                "Do not include greeting/salutation/polite expressions in summary.",
                "With make it easier to read."
                f"Write in {language}.", "", text
            ])
        }])

    if DEBUG:
        print(response["choices"][0]["message"]['content'])
    return response["choices"][0]["message"]['content']


def get_time_range():
    """
    Get a time range starting from 25 hours ago and ending at the current time.

    Returns:
        tuple: A tuple containing the start and end times of the time range, as datetime objects.

    Examples:
        >>> start_time, end_time = get_time_range()
        >>> print(start_time, end_time)
        2022-05-17 09:00:00+09:00 2022-05-18 10:00:00+09:00
    """
    hours_back = 25
    timezone = pytz.timezone(TIMEZONE_STR)
    now = datetime.now(timezone)
    yesterday = now - timedelta(hours=hours_back)
    start_time = datetime(yesterday.year, yesterday.month, yesterday.day,
                          yesterday.hour, yesterday.minute, yesterday.second)
    end_time = datetime(now.year, now.month, now.day, now.hour, now.minute,
                        now.second)
    return start_time, end_time


def estimate_openai_chat_token_count(text: str) -> int:
    """
    Estimate the number of OpenAI API tokens that would be consumed by sending the given text to the chat API.

    Args:
        text (str): The text to be sent to the OpenAI chat API.

    Returns:
        int: The estimated number of tokens that would be consumed by sending the given text to the OpenAI chat API.

    Examples:
        >>> estimate_openai_chat_token_count("Hello, how are you?")
        7
    """
    # Split the text into words and count the number of characters of each type
    pattern = re.compile(
        r"""(
            \d+       | # digits
            [a-z]+    | # alphabets
            \s+       | # whitespace
            .           # other characters
            )""", re.VERBOSE | re.IGNORECASE)
    matches = re.findall(pattern, text)

    # based on https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
    def counter(tok):
        if tok == ' ' or tok == '\n':
            return 0
        elif tok.isdigit() or tok.isalpha():
            return (len(tok) + 3) // 4
        else:
            return 1

    return sum(map(counter, matches))


def split_messages_by_token_count(messages: list[str]) -> list[list[str]]:
    """
    Split a list of strings into sublists with a maximum token count.

    Args:
        messages (list[str]): A list of strings to be split.

    Returns:
        list[list[str]]: A list of sublists, where each sublist has a token count less than or equal to max_body_tokens.
    """
    body_token_counts = [
        estimate_openai_chat_token_count(message) for message in messages
    ]
    result = []
    current_sublist = []
    current_count = 0

    for message, count in zip(messages, body_token_counts):
        if current_count + count <= MAX_BODY_TOKENS:
            current_sublist.append(message)
            current_count += count
        else:
            result.append(current_sublist)
            current_sublist = [message]
            current_count = count

    result.append(current_sublist)
    return result


# Load settings from environment variables
OPEN_AI_TOKEN = str(os.environ.get('OPEN_AI_TOKEN')).strip()
SLACK_BOT_TOKEN = str(os.environ.get('SLACK_BOT_TOKEN')).strip()
CHANNEL_ID = str(os.environ.get('SLACK_POST_CHANNEL_ID')).strip()
LANGUAGE = str(os.environ.get('LANGUAGE') or "Japanese").strip()
TIMEZONE_STR = str(os.environ.get('TIMEZONE') or 'Asia/Tokyo').strip()
TEMPERATURE = float(os.environ.get('TEMPERATURE') or 0.3)
CHAT_MODEL = str(os.environ.get('CHAT_MODEL') or "gpt-3.5-turbo").strip()
DEBUG = str(os.environ.get('DEBUG') or "").strip() != ""
MAX_BODY_TOKENS = 3000

if OPEN_AI_TOKEN == "" or SLACK_BOT_TOKEN == "" or CHANNEL_ID == "":
    print("OPEN_AI_TOKEN, SLACK_BOT_TOKEN, CHANNEL_ID must be set.")
    sys.exit(1)

# Set OpenAI API key
openai.api_key = OPEN_AI_TOKEN


def runner():
    """
    app runner
    """
    slack_client = SlackClient(slack_api_token=SLACK_BOT_TOKEN,
                               summary_channel=CHANNEL_ID)
    start_time, end_time = get_time_range()

    result_text = []
    for channel in slack_client.channels:
        if DEBUG:
            print(channel["name"])
        messages = slack_client.load_messages(channel["id"], start_time,
                                              end_time)
        if messages is None:
            continue

        # remove emojis in messages
        messages = list(map(remove_emoji, messages))

        result_text.append(f"----\n<#{channel['id']}>\n")
        for splitted_messages in split_messages_by_token_count(messages):
            text = summarize("\n".join(splitted_messages), LANGUAGE)
            result_text.append(text)

    title = (f"{start_time.strftime('%Y-%m-%d')} public channels summary\n\n")

    if DEBUG:
        print("\n".join(result_text))
    else:
        retry(lambda: slack_client.postSummary(title + "\n".join(result_text)),
              exception=SlackApiError)


if __name__ == '__main__':
    runner()
