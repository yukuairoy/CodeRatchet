from coderatchet.core.recent_failures import get_recently_broken_ratchets

# Test performance with limit
failures = get_recently_broken_ratchets(
    limit=100,
    include_commits=True,
)
