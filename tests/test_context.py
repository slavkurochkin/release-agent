import asyncio

from release_agent.context.github import MockGitHubClient

mock_data = {
    "myorg/api": {
        42: {
            "repo": "myorg/api",
            "pr_number": 42,
            "title": "Add caching layer",
            "author": "dev1",
            "files_changed": [
                {"path": "src/cache.py", "additions": 100, "deletions": 0}
            ],
            "commit_messages": ["feat: add Redis caching for hot paths"],
        }
    }
}

async def main():
    client = MockGitHubClient(mock_data=mock_data)
    result = await client.get_pr_data("myorg/api", 42)
    assert result.title == "Add caching layer"
    assert len(result.files_changed) == 1
    print("Mock client works correctly.")

asyncio.run(main())
