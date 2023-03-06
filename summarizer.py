#!/usr/bin/env python3
# https://github.com/masuidrive/slack-summarizer
# by [masuidrive](https://twitter.com/masuidrive) @ [Bloom&Co., Inc.](https://www.bloom-and-co.com/) 2023- [APACHE LICENSE, 2.0](https://www.apache.org/licenses/LICENSE-2.0)
import os
import re
import sys
import time
from datetime import datetime, timedelta
import pytz
import openai
import emoji
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient


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


def get_users_info() -> list:
    """
    Retrieve information about all users in the Slack workspace.

    Returns:
        list: A list of dictionaries containing information about each user,
            including their ID, name, and other metadata.

    Raises:
        SlackApiError: If an error occurs while attempting to retrieve the user information.

    Examples:
        >>> users = get_users_info()
        >>> print(users[0])
        {
            'id': 'U12345678',
            'name': 'alice',
            'real_name': 'Alice Smith',
            'email': 'alice@example.com',
            ...
        }
    """
    try:
        users = []
        next_cursor = None
        while True:
            users_info = slack_client.users_list(cursor=next_cursor, limit=100)
            time.sleep(3)
            users.extend(users_info['members'])
            if users_info["response_metadata"]["next_cursor"]:
                next_cursor = users_info["response_metadata"]["next_cursor"]
            else:
                break
        return users
    except SlackApiError as error:
        print(f"Error : {error}")
        sys.exit(1)


def get_channels_info() -> list:
    """
    Retrieve information about all public channels in the Slack workspace.

    Returns:
        list: A list of dictionaries containing information about each public channel, including its ID, name, and other metadata.

    Raises:
        SlackApiError: If an error occurs while attempting to retrieve the channel information.

    Examples:
        >>> channels = get_channels_info()
        >>> print(channels[0])
        {
            'id': 'C12345678',
            'name': 'general',
            'is_channel': True,
            'is_archived': False,
            ...
        }
    """
    try:
        result = slack_client.conversations_list(types="public_channel",
                                                 exclude_archived=True,
                                                 limit=1000)
        channels_info = [
            channel for channel in result['channels']
            if not channel["is_archived"] and channel["is_channel"]
        ]

        def sort_by_channel_name(lst):

            def is_digit_first(s):
                return s and s[0].isdigit()

            def key(obj):
                s = obj["name"]
                if is_digit_first(s):
                    # 数字が続く限り文字列を取り出して数値に変換
                    i = 0
                    while i < len(s) and s[i].isdigit():
                        i += 1
                    return (int(s[:i]), s)
                else:
                    return (float('inf'), s)

            return sorted(lst, key=key)

        return sort_by_channel_name(channels_info)
    except SlackApiError as error:
        print(f"Error : {error}")
        sys.exit(1)


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


def load_messages(channel_id: str, start_time: datetime, end_time: datetime,
                  users: list) -> list:
    """
    Load the chat history for the specified channel between the given start and end times.

    Args:
        channel_id (str): The ID of the channel to retrieve the chat history for.
        start_time (datetime): The start time of the time range to retrieve chat history for.
        end_time (datetime): The end time of the time range to retrieve chat history for.
        users (list): A list of dictionaries containing information about each user in the Slack workspace.

    Returns:
        list: A list of chat messages from the specified channel, in the format "Speaker: Message".

    Examples:
        >>> start_time = datetime(2022, 5, 1, 0, 0, 0)
        >>> end_time = datetime(2022, 5, 2, 0, 0, 0)
        >>> users = get_users_info()
        >>> messages = load_messages('C12345678', start_time, end_time, users)
        >>> print(messages[0])
        "Alice: Hi, Bob! How's it going?"
    """
    messages_info = []
    try:
        result = slack_client.conversations_history(
            channel=channel_id,
            oldest=start_time.timestamp(),
            latest=end_time.timestamp(),
            limit=1000)
        messages_info.extend(result["messages"])
    except SlackApiError as error:
        if error.response['error'] == 'not_in_channel':
            response = slack_client.conversations_join(channel=channel_id)
            if not response["ok"]:
                print("Failed conversations_join()")
                sys.exit(1)

            time.sleep(5)

            result = slack_client.conversations_history(
                channel=channel_id,
                oldest=start_time.timestamp(),
                latest=end_time.timestamp(),
                limit=1000)
        else:
            print(f"Error : {error}")
            return None

    # conversations_history API limit is 20 per minute
    time.sleep(3)

    while result["has_more"]:
        result = slack_client.conversations_history(
            channel=channel_id,
            oldest=start_time.timestamp(),
            latest=end_time.timestamp(),
            limit=1000,
            cursor=result["response_metadata"]["next_cursor"])
        messages_info.extend(result["messages"])
        time.sleep(3)  # this api limit is 20 per minute

    # Filter for human messages only
    messages = list(filter(lambda m: "subtype" not in m, messages_info))

    if len(messages) < 1:
        return None

    messages_text = []
    for message in messages[::-1]:
        # Ignore bot messages and empty messages
        if "bot_id" in message or len(message["text"].strip()) == 0:
            continue

        # Get speaker name
        speaker_name = get_user_name(message["user"], users) or "somebody"

        # Get message body fro result dict.
        body_text = message["text"].replace("\n", "\\n")

        # Replace User IDs in a chat message text with user names.
        body_text = replace_user_id_with_name(body_text, users)

        # all channel id replace to "other channel"
        body_text = re.sub(r"<#[A-Z0-9]+>", " other channel ", body_text)

        messages_text.append(f"{speaker_name}: {body_text}")

    if len(messages_text) == 0:
        return None
    else:
        return messages_text


def get_user_name(user_id: str, users: list) -> str:
    """
    Get the name of a user with the given ID.

    Args:
        user_id (str): The ID of the user to look up.
        users (list): A list of user information dictionaries. Each dictionary must have 'id' and 'name' keys.

    Returns:
        str: The name of the user with the given ID, or None if no such user exists.

    Examples:
        >>> users = [{'id': 'U1234', 'name': 'Alice'}, {'id': 'U5678', 'name': 'Bob'}]
        >>> get_user_name('U1234', users)
        'Alice'
        >>> get_user_name('U9999', users)
        None
    """
    matching_users = [user for user in users if user['id'] == user_id]
    return matching_users[0]['name'] if len(matching_users) > 0 else None


def replace_user_id_with_name(body_text: str, users: list) -> str:
    """
    Replace user IDs in a chat message text with user names.

    Args:
        body_text (str): The text of a chat message.
        users (list): A list of user information dictionaries.
            Each dictionary must have 'id' and 'name' keys.

    Returns:
        str: The text of the chat message with user IDs replaced with user names.

    Examples:
        >>> users = [{'id': 'U1234', 'name': 'Alice'}, {'id': 'U5678', 'name': 'Bob'}]
        >>> body_text = "Hi <@U1234>, how are you?"
        >>> replace_user_id_with_name(body_text, users)
        "Hi @Alice, how are you?"
    """
    pattern = r"<@([A-Z0-9]+)>"
    for match in re.finditer(pattern, body_text):
        user_id = match.group(1)
        user_name = next(
            (user['name'] for user in users if user['id'] == user_id), user_id)
        body_text = body_text.replace(match.group(0), user_name)
    return body_text


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

# Slack API Client
slack_client = WebClient(token=SLACK_BOT_TOKEN)


def runner():
    """
    app runner
    """
    start_time, end_time = get_time_range()
    channels = get_channels_info()
    users = get_users_info()
    time.sleep(3)

    result_text = []
    for channel in channels:
        if DEBUG:
            print(channel["name"])
        messages = load_messages(channel["id"], start_time, end_time, users)
        if messages is None:
            continue

        # remove emojis in messages
        messages = list(map(remove_emoji, messages))

        result_text.append(f"----\n<#{channel['id']}>\n")
        for spilitted_messages in split_messages_by_token_count(messages):
            text = summarize("\n".join(spilitted_messages), LANGUAGE)
            result_text.append(text)

    title = (f"{start_time.strftime('%Y-%m-%d')} public channels summary\n\n")

    if DEBUG:
        print("\n".join(result_text))
    else:
        response = slack_client.chat_postMessage(channel=CHANNEL_ID,
                                                 text=title +
                                                 "\n".join(result_text))
        if not response["ok"]:
            print("Failed to post message: ", response["error"])
            sys.exit(1)


if __name__ == '__main__':
    runner()
