# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


def exclude_items_from_user_input(
    L: list,
    messages: list[str] = [
        "List of items:",
        'Items to exclude: (eg: "1 2 3", "1-3", "^4" or item value)',
    ],
) -> list:
    """
    Get a list of repositories to exclude from the list of repositories to be migrated.

    Args:
        L (list): Initial list of items.
        messages ([str]): List of messages to display to the user.

    Return:
        :return: List of items excluding the ones specified by the user.
        :rtype: list
    """
    print(messages[0])
    for i, item in enumerate(L):
        print(f"{i}. {item}")

    print(messages[1])
    user_input = input().split()

    exclusion_indexes = []

    for item in user_input:
        if item.startswith("^"):
            return [L[int(item[1:])]]
        elif "-" in item and item[0].isdigit() and item[-1].isdigit():
            start, end = item.split("-")
            exclusion_indexes.extend(range(int(start), int(end) + 1))
        elif item.isdigit():
            exclusion_indexes.append(int(item))
        else:
            exclusion_indexes.append(L.index(item))

    return [k for i, k in enumerate(L) if i not in exclusion_indexes]


def choose_platform(L: list[str], source: bool):
    """
    Prompt the user to choose a platform from a list of platforms.

    Args:
        L (list[str]): List of platforms.
        source (bool): Whether the platform is a source or destination.

    Returns:
        str: The chosen platform.
    """
    if source:
        print("Select your source platform:")
    else:
        print("Select your destination platform:")
    for i, item in enumerate(L):
        print(f"{i+1}. {item}")
    user_input = int(input())
    return L[user_input - 1]
