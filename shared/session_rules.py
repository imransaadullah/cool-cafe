"""Session resume rules shared by server and client."""

import math


MIN_REMAINING_MINUTES_TO_RESUME = 5
MINUTES_PER_RESUME_SLOT = 30


def max_allowed_resumes(duration_minutes: float) -> int:
    """
    Allowed logout/resume cycles for a session.

    30 min → 1 resume, 60 min → 2, +1 for each additional 30 minutes.
    """
    return max(1, math.ceil(duration_minutes / MINUTES_PER_RESUME_SLOT))


def resumes_remaining(duration_minutes: float, resume_count: int) -> int:
    return max(0, max_allowed_resumes(duration_minutes) - resume_count)
