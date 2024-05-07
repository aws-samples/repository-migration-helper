# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import argparse
import logging
import boto3
from git import Repo, GitCommandError
from shutil import rmtree

user_messages = [
    """
List of CodeCommit repositories in the source account:
""",
    """
Repositories to exclude: (eg: "1 2 3", "1-3", "^4" or repo name)
Note: This list will be used to filter the list of repositories to be migrated.
Note: If you want to migrate all repositories, leave this field empty.
""",
]


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


def validate_session(session: boto3.Session) -> bool:
    """
    Validates the provided session by checking if the caller identity can be retrieved.

    Args:
        session (boto3.Session): The session to validate.

    Returns:
        bool: True if the session is valid, False otherwise.
    """
    try:
        # Get caller identity using the provided session
        sts_client = session.client("sts")
        caller_identity = sts_client.get_caller_identity()

        # If the above operation succeeded, the session is valid
        logging.info("Session is valid.")
        logging.info(f"Caller identity: {caller_identity}")
        return True
    except Exception as e:
        # If an exception occurred, the session is not valid
        logging.error(f"Session validation failed. Error: {str(e)}")
        return False


def main(
    source_profile: str,
    destination_profile: str,
    repo_prefix: str,
    migrate_all: bool = False,
    source_region: str = "",
    destination_region: str = "",
    dry_run: bool = False,
):
    """
    Migrates all codecommit repositories from one AWS account to another.

    Args:
        source_profile (str): The name of the AWS profile to migrate from.
        destination_profile (str): The name of the AWS profile to migrate to.
        repo_prefix (str): The prefix to add to the repository names in the destination account.
        source_region (str): The AWS region to use for the source account.
        destination_region (str): The AWS region to use for the destination account.
    """

    if len(repo_prefix) > 0 and repo_prefix[-1] != "-":
        repo_prefix = repo_prefix + "-"

    # Create sessions for the source and destination accounts, use the default regions if not specified
    if len(source_region) > 0:
        source_session = boto3.Session(
            profile_name=source_profile, region_name=source_region
        )
    else:
        source_session = boto3.Session(profile_name=source_profile)
        source_region = source_session.region_name
    if len(destination_region) > 0:
        destination_session = boto3.Session(
            profile_name=destination_profile, region_name=destination_region
        )
    else:
        destination_session = boto3.Session(profile_name=destination_profile)
        destination_region = destination_session.region_name

    # Check if the sessions are valid
    source_is_valid = validate_session(source_session)
    destination_is_valid = validate_session(destination_session)
    if not source_is_valid or not destination_is_valid:
        logging.error(
            "One or more sessions are invalid, please check you are using the correct profile and/or region"
        )
        return 1

    source_codecommit_client = source_session.client("codecommit")
    destination_codecommit_client = destination_session.client("codecommit")

    # Get a list of repositories in the source account
    source_repository_list = []
    list_repositories_response = source_codecommit_client.list_repositories()
    source_repository_list.extend(
        repo.get("repositoryName")
        for repo in list_repositories_response.get("repositories", [])
    )
    # Cycling through potential pagination of the repository list (batch sizes are 1000 for list repositories operations)
    while "nextToken" in list_repositories_response:
        list_repositories_response = source_codecommit_client.list_repositories(
            nextToken=list_repositories_response["nextToken"]
        )
        source_repository_list.extend(
            repo.get("repositoryName")
            for repo in list_repositories_response.get("repositories", [])
        )

    # If no repositories are found, print a warning and exit the program
    if len(source_repository_list) == 0:
        logging.warning(
            "No repositories found in the source account, please check you are using the correct profile and/or region"
        )
        return 0

    # If not specified otherwise, ask the user about repositories to exclude from the list of repositories to be migrated
    if migrate_all:
        to_migrate_repository_list = source_repository_list
    else:
        to_migrate_repository_list = exclude_items_from_user_input(
            source_repository_list, user_messages
        )

        # Final validation from the user
        print("List of selected repositories to be migrated:")
        for i, item in enumerate(to_migrate_repository_list):
            print(f"{i}. {item}")
        confirm = input("Do you want to proceed with migration? (yes/no): ").lower()
        if confirm not in ["yes", "y"]:
            logging.error("Migration aborted.")
            return 1

    if dry_run:
        logging.info("Dry run enabled, not migrating any repositories.")
        return 0

    try:
        # Loop over each repository to migrate
        for i, repo in enumerate(to_migrate_repository_list):
            logging.info(
                "Migrating repository {}/{}: {}".format(
                    i + 1, len(to_migrate_repository_list), repo
                )
            )

            try:
                # Try if a repository with the same name already exists in the destination account
                destination_codecommit_client.get_repository(
                    repositoryName=f"{repo_prefix}{repo}"
                )
                logging.warning(
                    f"{repo_prefix}{repo} already exists in destination, ignoring"
                )

            except (
                destination_codecommit_client.exceptions.RepositoryDoesNotExistException
            ):
                # If the repository does not exist in the destination account, create it and migrate the contents
                logging.debug(f"Cloning {repo} from source")

                # Fetch source repository details
                repository_info = source_codecommit_client.get_repository(
                    repositoryName=repo
                )

                # Clone the repository locally to the temporary directory
                git_repo = Repo.clone_from(
                    url=f"codecommit::{source_region}://{source_profile}@{repo}",
                    to_path=f"./tmp/{repo}",
                    allow_unsafe_protocols=True,
                    mirror=True,
                )

                # Create the repository in the destination account with the same name and description as the source repository
                destination_repository = (
                    destination_codecommit_client.create_repository(
                        repositoryName=f"{repo_prefix}{repo}",
                        repositoryDescription=repository_info.get(
                            "repositoryMetadata", {}
                        ).get("repositoryDescription", ""),
                    )
                )

                # Add it as a remote to the local repository clone
                remote = git_repo.create_remote(
                    "destination",
                    url=f"codecommit::{destination_region}://{destination_profile}@{repo_prefix}{repo}",
                    allow_unsafe_protocols=True,
                )

                # Push the repository content to the destination remote
                logging.debug(f"Pushing {repo} to destination")
                try:
                    remote.push(allow_unsafe_protocols=True, all=True)
                except GitCommandError as ex:
                    logging.warning(
                        f"Failed to push {repo} to destination, do you need to set up security pre-commits before pushing to remote?\n{ex}"
                    )
                    return 1
                except Exception as ex:
                    logging.error(f"An unexpected error occurred: {ex}")
                    return 1

                # Delete the local repository clone after it has been migrated
                rmtree(f"./tmp/{repo}")

        logging.info("All repositories have been migrated successfully")

    finally:
        # Delete the temporary directory after all repositories have been migrated
        rmtree("./tmp", ignore_errors=True)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source_profile",
        required=True,
        help="Name of the AWS CLI profile with required access to the source account",
    )
    parser.add_argument(
        "--destination_profile",
        required=True,
        help="Name of the AWS CLI profile with required access to the destination account",
    )
    parser.add_argument(
        "--repo_prefix", default="", help="Prefix to destination repositories name"
    )
    parser.add_argument(
        "--migrate_all",
        action="store_true",
        help="Set this if you want to migrate all repositories from the source account (bypasses the user exclude input)",
    )
    parser.add_argument(
        "--source_region",
        default="",
        help="AWS Region of the Source Account (default: Source Account CLI Profile)",
    )
    parser.add_argument(
        "--destination_region",
        default="",
        help="Targeted AWS Region on the Destination Account (default: Destination Account CLI Profile)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Simulate the migration without making changes",
    )
    parser.add_argument(
        "--log_level",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    args = parser.parse_args()

    if not args.source_profile.strip() or not args.destination_profile.strip():
        logging.error("Error: Source and destination profiles cannot be empty.")
        raise ValueError

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    main(
        args.source_profile,
        args.destination_profile,
        args.repo_prefix,
        migrate_all=args.migrate_all,
        source_region=args.source_region,
        destination_region=args.destination_region,
        dry_run=args.dry_run,
    )
