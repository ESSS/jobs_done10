from jobs_done10.repository import Repository


def testNameFromURL():
    tests = [
        ("/path/to/repo.git/", "repo"),
        ("file:///path/to/repo.git/", "repo"),
        ("file://~/path/to/repo.git/", "repo"),
        ("git://host.xz/path/to/repo.git/", "repo"),
        ("git://host.xz/~user/path/to/repo.git/", "repo"),
        ("host.xz:/path/to/repo.git/", "repo"),
        ("host.xz:path/to/repo.git", "repo"),
        ("host.xz:~user/path/to/repo.git/", "repo"),
        ("http://host.xz/path/to/repo.git/", "repo"),
        ("https://host.xz/path/to/repo.git/", "repo"),
        ("path/to/repo.git/", "repo"),
        ("rsync://host.xz/path/to/repo.git/", "repo"),
        ("ssh://host.xz/path/to/repo.git/", "repo"),
        ("ssh://host.xz/path/to/repo.git/", "repo"),
        ("ssh://host.xz/~/path/to/repo.git", "repo"),
        ("ssh://host.xz/~user/path/to/repo.git/", "repo"),
        ("ssh://host.xz:port/path/to/repo.git/", "repo"),
        ("ssh://user@host.xz/path/to/repo.git/", "repo"),
        ("ssh://user@host.xz/path/to/repo.git/", "repo"),
        ("ssh://user@host.xz/~/path/to/repo.git", "repo"),
        ("ssh://user@host.xz/~user/path/to/repo.git/", "repo"),
        ("ssh://user@host.xz:port/path/to/repo.git/", "repo"),
        ("user@host.xz:/path/to/repo.git/", "repo"),
        ("user@host.xz:path/to/repo.git", "repo"),
        ("user@host.xz:~user/path/to/repo.git/", "repo"),
        ("~/path/to/repo.git", "repo"),
    ]

    for url, expected_name in tests:
        assert Repository(url=url).name == expected_name, 'Failed for url "%s"' % url
