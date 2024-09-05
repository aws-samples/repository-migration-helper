# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
from getpass import getpass
from typing import Optional

from github import Auth, Github
from github.AuthenticatedUser import AuthenticatedUser
from platform_modules.platform_interface import GitPlatform


class GithubModule(GitPlatform):

    def __init__(self, *args, **kwargs):
        super().__init__(self)
        self.prompt_config()
        auth = Auth.Token(self.token)
        self.session = (
            Github(auth=auth, base_url=f"https://{self.custom_hostname}/api/v3")
            if self.custom_hostname
            else Github(auth=auth)
        )
        self.client = (
            self.session.get_organization(self.organization)
            if self.organization
            else self.session.get_user()
        )

    def prompt_config(self):
        self.token = getpass("Please enter the Github Personal Access Token:")
        print(
            "Please enter the Github Custom Hostname (leave blank for default github.com):"
        )
        self.custom_hostname = input()
        print(
            "Please enter the Github Organization (leave blank for user repositories):"
        )
        self.organization = input()

    def list_repositories(self) -> list[str]:
        """
        Lists all Github repositories in the account.

        Returns:
            list: A list of repository names.
        """
        # Get a list of repositories in the source account
        list_repositories_response = (
            self.client.get_repos(affiliation="owner")
            if isinstance(self.client, AuthenticatedUser)
            else self.client.get_repos()
        )
        repository_list = [repo.name for repo in list_repositories_response]

        return repository_list

    def get_repository(self, repository_name: str) -> dict:
        """
        Gets a Github repository object.

        Args:
            repository_name (str): The name of the repository to get.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.get_repo(name=repository_name)
        output = {
            "repository_name": repository_info.name,
            "repository_description": (
                repository_info.description if repository_info.description else ""
            ),
            "clone_url": repository_info.clone_url,
        }
        return output

    def create_repository(
        self, repository_name: str, repository_description: Optional[str]
    ) -> dict:
        """
        Creates a Github repository.

        Args:
            repository_name (str): The name of the repository to create.
            repository_description (Optional[str]): The description of the repository to create.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.create_repo(
            name=repository_name, description=repository_description, private=True
        )
        output = {
            "repository_name": repository_info.name,
            "repository_description": repository_info.description,
            "clone_url": repository_info.clone_url,
        }
        return output
