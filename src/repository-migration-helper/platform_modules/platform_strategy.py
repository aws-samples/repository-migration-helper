# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from platform_modules.codecommit import CodecommitModule
from platform_modules.github import GithubModule
from platform_modules.gitlab import GitlabModule

PLATFORMS = ["codecommit", "github", "gitlab"]


def get_platform_client(platform: str):

    match platform:
        case "codecommit":
            return CodecommitModule()
        case "github":
            return GithubModule()
        case "gitlab":
            return GitlabModule()
        case _:
            raise Exception("Non supported git platform")
