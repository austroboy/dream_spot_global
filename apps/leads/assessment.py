"""Indicative eligibility engine for the free assessment (SRS FR-ASM-03)."""
from decimal import Decimal

MIN_SCORES = {   # indicative IELTS-equivalent minimums by destination
    "united-kingdom": Decimal("6.0"), "australia": Decimal("6.0"), "canada": Decimal("6.0"),
    "usa": Decimal("6.0"), "germany": Decimal("6.5"), "finland": Decimal("6.0"),
    "ireland": Decimal("6.0"), "new-zealand": Decimal("6.0"),
}
NO_TEST_FRIENDLY = {"united-kingdom", "ireland", "canada"}   # MOI often accepted


def _norm_score(test, score):
    if score is None:
        return None
    score = Decimal(str(score))
    if test == "ielts":
        return score
    if test == "pte":
        return Decimal("6.5") if score >= 58 else Decimal("6.0") if score >= 50 else Decimal("5.0")
    if test == "toefl":
        return Decimal("6.5") if score >= 79 else Decimal("6.0") if score >= 60 else Decimal("5.0")
    if test == "duolingo":
        return Decimal("6.5") if score >= 110 else Decimal("6.0") if score >= 95 else Decimal("5.0")
    return None


def assess(*, destinations, study_level, gpa=None, english_test="none", english_score=None,
           work_experience_years=0, has_visa_refusal=False, backlogs=0):
    """Returns a dict stored on the lead and emailed to the student."""
    normalised = _norm_score(english_test, english_score)
    matched, review = [], []
    for country in destinations:
        slug = country.slug
        needed = MIN_SCORES.get(slug, Decimal("6.0"))
        if normalised is None:
            (matched if slug in NO_TEST_FRIENDLY else review).append(country.name)
        elif normalised >= needed:
            matched.append(country.name)
        else:
            review.append(country.name)

    strengths, actions = [], []
    if gpa:
        gpa = Decimal(str(gpa))
        if gpa >= Decimal("4.0"):
            strengths.append("Strong academic result")
        elif gpa < Decimal("3.0"):
            actions.append("Your academic result is on the lower side — we will shortlist "
                           "universities with flexible entry criteria.")
    if normalised and normalised >= Decimal("7.0"):
        strengths.append("Excellent English proficiency")
    if english_test == "none":
        actions.append("Book an IELTS or PTE test, or ask us about MOI-accepting universities.")
    if work_experience_years and Decimal(str(work_experience_years)) >= 2:
        strengths.append("Relevant work experience strengthens your application")
    if has_visa_refusal:
        actions.append("A previous refusal needs a carefully written explanation letter — "
                       "our visa team will prepare this with you.")
    if backlogs and int(backlogs) > 3:
        actions.append("Multiple backlogs limit some universities; we will target "
                       "institutions that accept your profile.")
    if not actions:
        actions.append("Upload your documents so we can begin shortlisting universities.")

    score = 40
    score += 20 if normalised and normalised >= Decimal("6.5") else 10 if normalised else 0
    score += 20 if gpa and Decimal(str(gpa)) >= Decimal("3.5") else 10 if gpa else 0
    score += 10 if work_experience_years and Decimal(str(work_experience_years)) >= 1 else 0
    score -= 15 if has_visa_refusal else 0
    score = max(15, min(95, score))

    return {
        "eligibility_score": score,
        "study_level": study_level,
        "matched_destinations": matched,
        "needs_review": review,
        "strengths": strengths,
        "recommended_actions": actions,
    }
