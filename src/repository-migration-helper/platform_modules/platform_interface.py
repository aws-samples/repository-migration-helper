# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from abc import ABC, abstractmethod


class GitPlatform(ABC):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.client = None

    @classmethod
    @abstractmethod
    def prompt_config(cls, **kwargs) -> None:
        """
        Prompts the user for the required configuration values.
        """
        pass

    @classmethod
    @abstractmethod
    def list_repositories(cls, **kwargs) -> list[str]:
        """
        Lists all repositories in the platform account.

        Returns:
            list: A list of repository names.
        """
        pass

    @classmethod
    @abstractmethod
    def get_repository(cls, repository_name, **kwargs) -> dict:
        """
        Gets a repository object.

        Args:
            repository_name (str): The name of the repository to get.

        Returns:
            dict: The repository object.
        """
        pass

    @classmethod
    @abstractmethod
    def create_repository(cls, repository_name, **kwargs) -> dict:
        """
        Creates a repository on the platform.

        Args:
            repository_name (str): The name of the repository to create.
            repository_description (Optional[str]): The description of the repository to create.

        Returns:
            dict: The repository object.
        """
        pass
