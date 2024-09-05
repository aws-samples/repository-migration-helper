# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import argparse
import logging
from shutil import rmtree

from git import GitCommandError, Repo
from platform_modules import PLATFORMS, get_platform_client
from utils import choose_platform, exclude_items_from_user_input

user_messages = [
    """
List of repositories in the source platform:
""",
    """
Repositories to exclude: (eg: "1 2 3", "1-3", "^4" or repo name)
Note: This list will be used to filter the list of repositories to be migrated.
Note: If you want to migrate all repositories, leave this field empty.
""",
]


def main(
    repo_prefix: str,
    migrate_all: bool = False,
    dry_run: bool = False,
):
    """
    Migrates all repositories from one Git platform to another.

    Args:
        source_profile (str): The name of the AWS profile to migrate from.
        destination_profile (str): The name of the AWS profile to migrate to.
        repo_prefix (str): The prefix to add to the repository names in the destination account.
        source_region (str): The AWS region to use for the source account.
        destination_region (str): The AWS region to use for the destination account.
    """

    if len(repo_prefix) > 0 and repo_prefix[-1] != "-":
        repo_prefix = repo_prefix + "-"

    source_platform = choose_platform(PLATFORMS, source=True)
    source_client = get_platform_client(platform=source_platform)

    # Get a list of repositories in the source account
    source_repository_list = source_client.list_repositories()

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

        if len(to_migrate_repository_list) > 0:
            # Final validation from the user
            print("List of selected repositories to be migrated:")
            for i, item in enumerate(to_migrate_repository_list):
                print(f"{i}. {item}")
            confirm = input(
                "Do you confirm the list of repositories to migrate? (yes/no): "
            ).lower()
            if confirm not in ["yes", "y"]:
                logging.error("Migration aborted.")
                return 1
        else:
            print("No repositories selected for migration.")
            return 0

    destination_platform = choose_platform(PLATFORMS, source=False)
    destination_client = get_platform_client(platform=destination_platform)

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
                destination_client.get_repository(
                    repository_name=f"{repo_prefix}{repo}"
                )
                logging.warning(
                    f"{repo_prefix}{repo} already exists in destination, ignoring"
                )

            except Exception:
                # If the repository does not exist in the destination account, create it and migrate the contents
                logging.debug(f"Cloning {repo} from source")

                # Fetch source repository details
                repository_info = source_client.get_repository(repository_name=repo)

                # Clone the repository locally to the temporary directory
                git_repo = Repo.clone_from(
                    url=repository_info.get("clone_url"),
                    to_path=f"./tmp/{repo}",
                    allow_unsafe_protocols=True,
                    mirror=True,
                )

                # Create the repository in the destination account with the same name and description as the source repository
                destination_repository = destination_client.create_repository(
                    repository_name=f"{repo_prefix}{repository_info.get("repository_name", repo)}",
                    repository_description=repository_info.get(
                        "repository_description", ""
                    ),
                )

                # Add it as a remote to the local repository clone
                remote = git_repo.create_remote(
                    "destination",
                    url=destination_repository.get("clone_url"),
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
        "--repo_prefix", default="", help="Prefix to destination repositories name"
    )
    parser.add_argument(
        "--migrate_all",
        action="store_true",
        help="Set this if you want to migrate all repositories from the source account (bypasses the user exclude input)",
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

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    main(
        args.repo_prefix,
        migrate_all=args.migrate_all,
        dry_run=args.dry_run,
    )
