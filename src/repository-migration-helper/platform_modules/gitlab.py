# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import logging
from getpass import getpass
from typing import Optional

from gitlab import Gitlab
from platform_modules.platform_interface import GitPlatform


class GitlabModule(GitPlatform):

    def __init__(self, *args, **kwargs):
        super().__init__(self)
        self.prompt_config()
        self.client = (
            Gitlab(private_token=self.token, url=self.custom_hostname)
            if self.custom_hostname
            else Gitlab(private_token=self.token)
        )
        self.client.auth()

    def prompt_config(self):
        self.token = getpass("Please enter the Gitlab Private Token:")
        print(
            "Please enter the Gitlab Custom Hostname (leave blank for default gitlab.com):"
        )
        self.custom_hostname = input()

    def list_repositories(self) -> list[str]:
        """
        Lists all Gitlab repositories in the account.

        Returns:
            list: A list of repository names.
        """
        # Get a list of repositories in the source account
        list_repositories_response = self.client.projects.list(owned=True)
        repository_list = [
            repo.path_with_namespace for repo in list_repositories_response
        ]

        return repository_list

    def get_repository(self, repository_name: str) -> dict:
        """
        Gets a Gitlab repository object.

        Args:
            repository_name (str): The name of the repository to get.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.projects.get(repository_name)
        output = {
            "repository_name": repository_info.name,
            "repository_description": repository_info.description,
            "clone_url": repository_info.ssh_url_to_repo,
        }
        return output

    def create_repository(
        self, repository_name: str, repository_description: Optional[str]
    ) -> dict:
        """
        Creates a Gitlab repository.

        Args:
            repository_name (str): The name of the repository to create.
            repository_description (Optional[str]): The description of the repository to create.

        Returns:
            dict: The repository object.
        """
        repository_info = self.client.projects.create(
            {
                "name": repository_name,
                "description": repository_description,
                "visibility": "private",
            }
        )
        output = {
            "repository_name": repository_info.name,
            "repository_description": repository_info.description,
            "clone_url": repository_info.ssh_url_to_repo,
        }
        return output
