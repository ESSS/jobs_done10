def get_version_title():
    import pkg_resources

    try:
        version = pkg_resources.get_distribution("jobs_done10").version
    except pkg_resources.DistributionNotFound:
        version = "<N/A>"
    return f"jobs_done10 ver. {version}"
