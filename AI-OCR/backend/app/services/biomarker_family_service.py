from typing import Dict, Any, List


def group_primary_biomarkers(biomarkers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups biomarkers by family and extracts only primary biomarkers for summaries/highlights.
    Rules:
    1. If a biomarker has 'family' and 'is_primary=False', and a primary biomarker with the same family exists,
       it is excluded from summary calculations.
    2. If no primary biomarker exists in that family, the highest priority biomarker is preserved.
    3. Non-family biomarkers are always included.
    """
    if not biomarkers:
        return []

    # Map family -> list of biomarkers in that family
    family_members: Dict[str, List[Dict[str, Any]]] = {}
    non_family: List[Dict[str, Any]] = []

    for bm in biomarkers:
        fam = bm.get("family")
        if fam:
            family_members.setdefault(fam, []).append(bm)
        else:
            non_family.append(bm)

    primary_biomarkers: List[Dict[str, Any]] = list(non_family)

    for fam, members in family_members.items():
        # Check if there is an explicit primary biomarker
        primaries = [m for m in members if m.get("is_primary") is True]
        if primaries:
            # Add only the primary biomarker(s)
            primary_biomarkers.extend(primaries)
        else:
            # Fallback to the first member or highest priority member
            primary_biomarkers.append(members[0])

    return primary_biomarkers
