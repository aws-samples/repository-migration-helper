# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
from typing import Optional

import boto3
from platform_modules.platform_interface import GitPlatform


class CodecommitModule(GitPlatform):

    def __init__(self, *args, **kwargs):
        super().__init__(self)
        # Create sessions for the codecommit account, use the default region if not specified
        self.prompt_config()
        if not self.profile:
            self.profile = "default"
        if self.region:
            self.session = boto3.Session(
                profile_name=self.profile, region_name=self.region
            )
        else:
            self.session = boto3.Session(profile_name=self.profile)
            self.region = self.session.region_name

        assert self.validate_session(session=self.session)
        self.client = self.session.client("codecommit")

    def prompt_config(self):
        print(
            "Please enter the AWS CLI Profile Name (leave blank for default profile):"
        )
        self.profile = input()
        print("Please enter the AWS Region (leave blank for default region):")
        self.region = input()

    def validate_session(self, session: boto3.Session) -> bool:
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

    def list_repositories(self) -> list[str]:
        """
        Lists all codecommit repositories in the AWS account.

        Returns:
            list: A list of repository names.
        """

        # Get a list of repositories in the source account
        repository_list = []
        list_repositories_response = self.client.list_repositories()
        repository_list.extend(
            repo.get("repositoryName")
            for repo in list_repositories_response.get("repositories", [])
        )
        # Cycling through potential pagination of the repository list (batch sizes are 1000 for list repositories operations)
        while "nextToken" in list_repositories_response:
            list_repositories_response = self.client.list_repositories(
                nextToken=list_repositories_response["nextToken"]
            )
            repository_list.extend(
                repo.get("repositoryName")
                for repo in list_repositories_response.get("repositories", [])
            )

        return repository_list

    def get_repository(self, repository_name: str) -> dict:
        """
        Gets a codecommit repository object.

        Args:
            repository_name (str): The name of the repository to get.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.get_repository(repositoryName=repository_name)
        output = {
            "repository_name": repository_info.get("repositoryMetadata").get(
                "repositoryName"
            ),
            "repository_description": repository_info.get("repositoryMetadata", {}).get(
                "repositoryDescription", ""
            ),
            "clone_url": f"codecommit::{self.region}://{self.profile}@{repository_name}",
        }
        return output

    def create_repository(
        self, repository_name: str, repository_description: Optional[str]
    ) -> dict:
        """
        Creates a codecommit repository.

        Args:
            repository_name (str): The name of the repository to create.
            repository_description (Optional[str]): The description of the repository to create.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.create_repository(
            repositoryName=repository_name, repositoryDescription=repository_description
        )
        output = {
            "repository_name": repository_info.get("repositoryMetadata").get(
                "repositoryName"
            ),
            "repository_description": repository_info.get("repositoryMetadata", {}).get(
                "repositoryDescription", ""
            ),
            "clone_url": f"codecommit::{self.region}://{self.profile}@{repository_name}",
        }
        return output
