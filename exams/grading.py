import math


# IELTS Academic Reading conversion commonly used for 40-question papers.
# Scores between published boundaries are represented in 0.5-band steps.
ACADEMIC_READING_BANDS = (
    (39, 9.0), (37, 8.5), (35, 8.0), (33, 7.5), (30, 7.0),
    (27, 6.5), (23, 6.0), (19, 5.5), (15, 5.0), (13, 4.5),
    (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5), (3, 2.0),
    (2, 1.5), (1, 1.0), (0, 0.0),
)


def academic_reading_band(correct, total=40):
    """Return (band, equivalent_40_score, is_estimate) for an objective Reading score."""
    if total <= 0:
        return None, None, False
    correct = max(0, min(int(correct), int(total)))
    if total == 40:
        equivalent = correct
        estimated = False
    else:
        # Round half upward so Python's banker rounding does not disadvantage
        # passage-sized practice scores at exact .5 boundaries.
        equivalent = min(40, math.floor((correct * 40 / total) + 0.5))
        estimated = True
    band = next(band for minimum, band in ACADEMIC_READING_BANDS if equivalent >= minimum)
    return band, equivalent, estimated
