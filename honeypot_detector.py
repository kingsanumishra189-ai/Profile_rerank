"""
Honeypot Detection Module
Identifies ~80 subtly impossible candidate profiles in the dataset.
These candidates are forced to score 0.05 (cannot make top 100).
"""

import re


class HoneypotDetector:
    """Detects honeypot (impossible/fake) candidate profiles."""

    def __init__(self):
        """Initialize honeypot detection patterns."""
        # Patterns for detecting impossible profiles
        self.suspicious_title_patterns = [
            r'ceo.*intern',
            r'founder.*entry.?level',
            r'principal.*junior',
            r'staff.*fresher',
        ]
        
        self.compile_patterns()

    def compile_patterns(self):
        """Pre-compile all regex patterns for performance."""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.suspicious_title_patterns
        ]

    def is_honeypot(self, candidate: dict) -> bool:
        """
        Check if a candidate profile is a honeypot.
        
        Args:
            candidate: Candidate data dictionary
            
        Returns:
            True if honeypot detected, False otherwise
        """
        checks = [
            self._check_impossible_title_progression(candidate),
            self._check_impossible_experience_claims(candidate),
            self._check_impossible_skill_depth(candidate),
            self._check_data_integrity_issues(candidate),
            self._check_impossible_timeline(candidate),
        ]
        
        return any(checks)

    def _check_impossible_title_progression(self, candidate: dict) -> bool:
        """Detect impossible title progressions (e.g., CEO at entry level)."""
        current_title = candidate.get('current_title', '').lower()
        
        for pattern in self.compiled_patterns:
            if pattern.search(current_title):
                return True
        
        # Check career history for contradictions
        career_history = candidate.get('career_history', [])
        if len(career_history) > 1:
            titles = [role.get('title', '').lower() for role in career_history]
            
            # Principal role followed by junior roles
            if any('principal' in t or 'staff' in t for t in titles[:2]):
                if any('junior' in t or 'intern' in t for t in titles[2:]):
                    return True
        
        return False

    def _check_impossible_experience_claims(self, candidate: dict) -> bool:
        """Detect candidates claiming impossible experience levels."""
        yoe = candidate.get('years_of_experience', 0)
        
        # More than 40 years of experience is suspicious
        if yoe > 40:
            return True
        
        # YOE mismatch with birth year
        birth_year = candidate.get('birth_year')
        if birth_year and yoe > (2026 - birth_year - 22):
            return True
        
        return False

    def _check_impossible_skill_depth(self, candidate: dict) -> bool:
        """Detect candidates with unrealistic skill depth."""
        skills = candidate.get('skills', [])
        
        # Check for impossible skill combinations or claims
        expert_count = 0
        for skill in skills:
            if skill.get('proficiency', '').lower() == 'expert':
                expert_count += 1
        
        # More than 20 expert skills is suspicious
        if expert_count > 20:
            return True
        
        # Skills with impossible durations (> 60 months for skills in last 2 years)
        for skill in skills:
            if skill.get('duration_months', 0) > 60:
                if not self._skill_in_career_history(candidate, skill.get('name', '')):
                    return True
        
        return False

    def _check_data_integrity_issues(self, candidate: dict) -> bool:
        """Detect data integrity issues suggesting honeypot."""
        # Missing critical fields
        if not candidate.get('candidate_id'):
            return True
        
        # Invalid contact info patterns
        email = candidate.get('email', '').lower()
        if email and not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
            return True
        
        # Impossible response rates
        response_rate = candidate.get('recruiter_response_rate', 0)
        if response_rate < 0 or response_rate > 1:
            return True
        
        # Invalid notification preference
        notification_pref = candidate.get('notification_preference', '').lower()
        if notification_pref and notification_pref not in ['email', 'sms', 'phone', 'push']:
            return True
        
        return False

    def _check_impossible_timeline(self, candidate: dict) -> bool:
        """Detect timeline inconsistencies."""
        career_history = candidate.get('career_history', [])
        
        total_duration = 0
        yoe = candidate.get('years_of_experience', 0)
        
        for role in career_history:
            duration = role.get('duration_months', 0)
            total_duration += duration
            
            # Role duration > 7 years (84 months)
            if duration > 84:
                return True
        
        # Total career duration significantly mismatches YOE
        career_years = total_duration / 12
        if career_years > 0 and abs(career_years - yoe) > 3:
            return True
        
        return False

    def _skill_in_career_history(self, candidate: dict, skill_name: str) -> bool:
        """Check if a skill appears in career history descriptions."""
        career_history = candidate.get('career_history', [])
        skill_lower = skill_name.lower()
        
        for role in career_history:
            description = role.get('description', '').lower()
            if skill_lower in description:
                return True
        
        return False
