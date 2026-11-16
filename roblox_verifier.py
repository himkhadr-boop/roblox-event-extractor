import difflib
import itertools
import json
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class RobloxVerifier:
    """
    Handles Roblox user identification, candidate disambiguation,
    and clan membership verification with roster pre-fetching.
    """

    def __init__(self, user_agent: str = "Mozilla/5.0"):
        self.headers = {"User-Agent": user_agent}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._groups_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._group_rosters: Dict[int, Dict[str, Dict[str, Any]]] = {}

    def get_group_members(
        self, group_id: int, refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetches and caches the entire roster of a Roblox group via cursor pagination.
        Caches roster mapping lowercased username to:
        {'username': canonical_name, 'userId': id, 'role': role_name}
        """
        if not group_id:
            return {}

        if not refresh and group_id in self._group_rosters:
            return self._group_rosters[group_id]

        roster: Dict[str, Dict[str, Any]] = {}
        cursor: Optional[str] = None

        while True:
            url = f"https://groups.roblox.com/v1/groups/{group_id}/users?limit=100"
            if cursor:
                url += f"&cursor={cursor}"
            try:
                resp = self.session.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning(f"Error fetching group members for group {group_id}: {e}")
                break

            for item in data.get("data", []):
                user = item.get("user", {})
                role = item.get("role", {})
                canonical_name = user.get("username")
                user_id = user.get("userId")
                role_name = role.get("name")
                if canonical_name:
                    roster[canonical_name.lower()] = {
                        "username": canonical_name,
                        "userId": user_id,
                        "role": role_name,
                    }

            cursor = data.get("nextPageCursor")
            if not cursor:
                break

        self._group_rosters[group_id] = roster
        return roster

    @staticmethod
    def generate_candidate_variants(username: str, max_candidates: int = 32) -> List[str]:
        """
        Generates candidate username variants to resolve sans-serif visual and OCR ambiguities:
        - Uppercase 'I' <-> Lowercase 'l' <-> Lowercase 'i' (e.g., Chaotic <-> Chaotlc, SAVIO_R <-> SAVlO_R)
        - Digit '0' <-> Uppercase 'O' / Lowercase 'o'
        - Kerning/ligatures: 'cl' <-> 'd', 'di' <-> 'cl' (e.g., flanked / Flankedi <-> flankecl)
        - Kerning: 'rn' <-> 'm'

        Preserves original username at index 0.
        Limits combinations to at most `max_candidates`.
        """
        rules = [
            ("I", "l"), ("I", "i"),
            ("l", "I"), ("l", "i"),
            ("i", "l"), ("i", "I"),
            ("0", "O"), ("0", "o"),
            ("O", "0"), ("o", "0"),
            ("cl", "d"), ("cl", "di"),
            ("d", "cl"), ("di", "cl"),
            ("CL", "D"), ("D", "CL"),
            ("rn", "m"), ("m", "rn"),
            ("RN", "M"), ("M", "RN"),
        ]

        candidates = [username]
        seen = {username.lower()}

        # 1. Single substitutions at each occurrence and all occurrences
        for target, rep in rules:
            if target in username:
                idx = 0
                while True:
                    pos = username.find(target, idx)
                    if pos == -1:
                        break
                    variant = username[:pos] + rep + username[pos + len(target):]
                    if variant.lower() not in seen:
                        seen.add(variant.lower())
                        candidates.append(variant)
                        if len(candidates) >= max_candidates:
                            return candidates
                    idx = pos + 1

                variant_all = username.replace(target, rep)
                if variant_all.lower() not in seen:
                    seen.add(variant_all.lower())
                    candidates.append(variant_all)
                    if len(candidates) >= max_candidates:
                        return candidates

        # 2. Combinations of substitutions from accumulated candidates
        for c in list(candidates):
            for target, rep in rules:
                if target in c:
                    variant = c.replace(target, rep)
                    if variant.lower() not in seen:
                        seen.add(variant.lower())
                        candidates.append(variant)
                        if len(candidates) >= max_candidates:
                            return candidates

        return candidates

    def batch_lookup_users(self, usernames: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Queries Roblox User API in batches (up to 100 per request).
        Maps both canonical name and requested username (lowercased) to user info:
        {'id': user_id, 'name': canonical_name, 'displayName': display_name}
        """
        if not usernames:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        chunk_size = 100
        url = "https://users.roblox.com/v1/usernames/users"

        for i in range(0, len(usernames), chunk_size):
            chunk = usernames[i : i + chunk_size]
            payload = {"usernames": chunk, "excludeBannedUsers": False}
            try:
                resp = self.session.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                for u in data:
                    user_info = {
                        "id": u.get("id"),
                        "name": u.get("name"),
                        "displayName": u.get("displayName"),
                    }
                    if "name" in u and u["name"]:
                        results[u["name"].lower()] = user_info
                    if "requestedUsername" in u and u["requestedUsername"]:
                        results[u["requestedUsername"].lower()] = user_info
            except Exception as e:
                logger.warning(f"Error querying Roblox batch users API: {e}")

        return results

    def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Queries Roblox Groups API for a user's group memberships and roles.
        Returns list of dicts: {'id': group_id, 'name': group_name, 'role': role_name}
        """
        if user_id in self._groups_cache:
            return self._groups_cache[user_id]

        url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            groups: List[Dict[str, Any]] = []
            for item in data:
                grp = item.get("group", {})
                role = item.get("role", {})
                groups.append({
                    "id": grp.get("id"),
                    "name": grp.get("name"),
                    "role": role.get("name"),
                })
            self._groups_cache[user_id] = groups
            return groups
        except Exception as e:
            logger.warning(f"Error fetching groups for Roblox user {user_id}: {e}")
            return []

    def verify_roster(
        self, usernames: List[str], target_group_id: int = 825966682
    ) -> List[Dict[str, Any]]:
        """
        Verifies a list of usernames against Roblox with clan-first matching:
        1. If target_group_id is provided, pre-fetches and caches group roster.
        2. Fast Clan-First matching:
           a. Direct lowercase match in clan roster.
           b. Visual/OCR candidate variant match in clan roster.
           c. difflib fuzzy match against clan roster.
        3. If not in clan, falls back to general Roblox batch lookup & disambiguation.

        Returns structured results:
        [{
            'raw': raw_username,
            'verified_name': canonical_name or None,
            'user_id': id or None,
            'in_clan': bool,
            'clan_role': role_name or None,
            'is_verified': bool
        }]
        """
        if not usernames:
            return []

        group_members = (
            self.get_group_members(target_group_id) if target_group_id else {}
        )

        results: List[Optional[Dict[str, Any]]] = [None] * len(usernames)
        unmatched_indices: List[int] = []

        for idx, u in enumerate(usernames):
            matched_clan_member: Optional[Dict[str, Any]] = None
            lower_name = u.lower()

            if group_members:
                # a. Direct lowercase match in group_members
                if lower_name in group_members:
                    matched_clan_member = group_members[lower_name]
                else:
                    # b. Any generated candidate in group_members
                    cands = self.generate_candidate_variants(u)
                    for cand in cands:
                        cand_lower = cand.lower()
                        if cand_lower in group_members:
                            matched_clan_member = group_members[cand_lower]
                            break

                    # c. Fuzzy match using difflib
                    if not matched_clan_member:
                        close_matches = difflib.get_close_matches(
                            lower_name, group_members.keys(), n=1, cutoff=0.75
                        )
                        if close_matches:
                            matched_clan_member = group_members[close_matches[0]]

            # d. If matched in clan
            if matched_clan_member:
                results[idx] = {
                    "raw": u,
                    "verified_name": matched_clan_member["username"],
                    "user_id": matched_clan_member["userId"],
                    "in_clan": True,
                    "clan_role": matched_clan_member["role"],
                    "is_verified": True,
                }
            else:
                unmatched_indices.append(idx)

        # e. If NOT in clan, fall back to existing general batch_lookup_users on Roblox
        if unmatched_indices:
            unmatched_cands: Dict[str, List[str]] = {}
            all_fallback_cands: List[str] = []

            for idx in unmatched_indices:
                u = usernames[idx]
                cands = self.generate_candidate_variants(u)
                unmatched_cands[u] = cands
                all_fallback_cands.extend(cands)

            lookup = self.batch_lookup_users(list(dict.fromkeys(all_fallback_cands)))

            for idx in unmatched_indices:
                u = usernames[idx]
                cands = unmatched_cands[u]
                existing: List[tuple[str, Dict[str, Any]]] = []
                seen_ids = set()

                for c in cands:
                    user_info = lookup.get(c.lower())
                    if user_info and user_info["id"] not in seen_ids:
                        seen_ids.add(user_info["id"])
                        existing.append((c, user_info))

                if not existing:
                    results[idx] = {
                        "raw": u,
                        "verified_name": None,
                        "user_id": None,
                        "in_clan": False,
                        "clan_role": None,
                        "is_verified": False,
                    }
                    continue

                chosen_user: Optional[Dict[str, Any]] = None
                in_clan = False
                clan_role: Optional[str] = None

                if len(existing) == 1:
                    cand_str, user_info = existing[0]
                    chosen_user = user_info
                    if target_group_id:
                        groups = self.get_user_groups(user_info["id"])
                        for g in groups:
                            if g.get("id") == target_group_id:
                                in_clan = True
                                clan_role = g.get("role")
                                break
                else:
                    clan_matches: List[tuple[str, Dict[str, Any], str]] = []
                    if target_group_id:
                        for cand_str, user_info in existing:
                            groups = self.get_user_groups(user_info["id"])
                            for g in groups:
                                if g.get("id") == target_group_id:
                                    clan_matches.append((cand_str, user_info, g.get("role")))
                                    break

                    if len(clan_matches) == 1:
                        cand_str, chosen_user, clan_role = clan_matches[0]
                        in_clan = True
                    elif len(clan_matches) > 1:
                        exact = [m for m in clan_matches if m[0] == u]
                        cand_str, chosen_user, clan_role = exact[0] if exact else clan_matches[0]
                        in_clan = True
                    else:
                        exact_existing = [e for e in existing if e[0] == u]
                        cand_str, chosen_user = exact_existing[0] if exact_existing else existing[0]
                        in_clan = False
                        clan_role = None

                results[idx] = {
                    "raw": u,
                    "verified_name": chosen_user["name"] if chosen_user else None,
                    "user_id": chosen_user["id"] if chosen_user else None,
                    "in_clan": in_clan,
                    "clan_role": clan_role,
                    "is_verified": True,
                }

        return [r for r in results if r is not None]


if __name__ == "__main__":
    verifier = RobloxVerifier()
    test_usernames = ["Flankedi", "MarikChaotic", "SAVIO_R"]
    target_group = 825966682  # Winslow Accord

    print(f"Verifying roster {test_usernames} against group {target_group}...")
    verified_roster = verifier.verify_roster(test_usernames, target_group_id=target_group)
    print("\nVerification Results:")
    print(json.dumps(verified_roster, indent=2))

    # Assertions for required resolutions
    expected = {
        "Flankedi": ("flankecl", "Private"),
        "MarikChaotic": ("MarikChaotlc", "Secretary-General"),
        "SAVIO_R": ("SAVlO_R", "Conscript"),
    }

    for item in verified_roster:
        raw = item["raw"]
        exp_name, exp_role = expected[raw]
        assert item["verified_name"] == exp_name, f"Expected {exp_name}, got {item['verified_name']}"
        assert item["clan_role"] == exp_role, f"Expected {exp_role}, got {item['clan_role']}"
        assert item["in_clan"] is True, f"Expected in_clan True for {raw}"
        assert item["is_verified"] is True, f"Expected is_verified True for {raw}"

    print("\nAll verification assertions passed successfully!")
