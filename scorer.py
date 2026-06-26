"""
Candidate Scorer Module
Implements the 5-component weighted scoring system.
"""

import re
from typing import List, Dict, Tuple
from honeypot_detector import HoneypotDetector
from signals import (
    behavioral_multiplier,
    keyword_stuffer_penalty,
    title_tier_score,
    experience_score,
    notice_period_score,
    location_score
)


class CandidateScorer:
    """Multi-component weighted scorer for candidate ranking."""

    def __init__(self):
        """Initialize scorer with pre-compiled patterns and keyword sets."""
        self.honeypot_detector = HoneypotDetector()
        
        # Component weights
        self.WEIGHTS = {
            'career_substance': 0.35,
            'skills_depth': 0.25,
            'title_role_fit': 0.20,
            'experience_calibration': 0.10,
            'location_logistics': 0.10,
        }
        
        # Pre-compile keyword patterns
        self._compile_keywords()
        
        # Consulting firms (disqualifiers)
        self.CONSULTING_FIRMS = {
            'tcs', 'tata consultancy', 'infosys', 'wipro', 'accenture',
            'cognizant', 'capgemini', 'hcl', 'tech mahindra', 'mindtree',
            'mphasis', 'hexaware', 'l&t infotech', 'ltimindtree',
            'persistent systems', 'deloitte', 'pwc', 'kpmg', 'ey'
        }
        
        # Skill definitions
        self.MUST_HAVE_SKILLS = {
            'python', 'embedding', 'vector', 'retrieval', 'ranking',
            'semantic search', 'pinecone', 'weaviate', 'qdrant', 'milvus',
            'faiss', 'elasticsearch', 'opensearch', 'chromadb', 'bm25',
            'nlp', 'llm', 'transformer', 'bert', 'gpt', 'fine-tun'
        }
        
        self.NICE_HAVE_SKILLS = {
            'xgboost', 'lightgbm', 'pytorch', 'tensorflow', 'sklearn',
            'mlflow', 'kubeflow', 'mlops', 'a/b test', 'ndcg', 'mrr',
            'lora', 'qlora', 'recommendation', 'learning to rank'
        }

    def _compile_keywords(self):
        """Pre-compile all regex patterns for performance."""
        self.STRONG_SIGNALS = {
            'embedding', 'vector search', 'semantic search', 'retrieval',
            'ranking system', 'recommendation system', 'faiss', 'pinecone',
            'qdrant', 'milvus', 'weaviate', 'elasticsearch', 'opensearch',
            'chromadb', 'bm25', 'hybrid search', 'fine-tun', 'lora', 'qlora',
            'ndcg', 'mrr', 'a/b test', 'rerank', 'cross-encoder', 'bi-encoder',
            'sentence-transformer', 'production', 'deployed', 'llm',
            'large language model', 'transformer', 'bert', 'gpt'
        }
        
        self.WEAK_SIGNALS = {
            'machine learning', 'deep learning', 'neural', 'model', 'pytorch',
            'tensorflow', 'sklearn', 'xgboost', 'lightgbm', 'nlp', 'python',
            'inference', 'mlflow', 'kubeflow', 'mlops', 'data pipeline',
            'feature engineering'
        }

    def score(self, candidate: dict) -> Tuple[float, str]:
        """
        Compute final score and reasoning for a candidate.
        
        Args:
            candidate: Candidate data dictionary
            
        Returns:
            Tuple of (final_score, reasoning_text)
        """
        # Check honeypot
        if self.honeypot_detector.is_honeypot(candidate):
            return 0.05, "Honeypot profile detected: impossible profile characteristics."
        
        # Compute component scores
        career_score = self._score_career_substance(candidate)
        skills_score = self._score_skills_depth(candidate)
        title_score = self._score_title_role_fit(candidate)
        experience_score_val = self._score_experience_calibration(candidate)
        location_score_val = self._score_location_logistics(candidate)
        
        # Weighted sum
        raw_score = (
            self.WEIGHTS['career_substance'] * career_score +
            self.WEIGHTS['skills_depth'] * skills_score +
            self.WEIGHTS['title_role_fit'] * title_score +
            self.WEIGHTS['experience_calibration'] * experience_score_val +
            self.WEIGHTS['location_logistics'] * location_score_val
        )
        
        # Apply behavioral multiplier
        behavior_mult = behavioral_multiplier(candidate)
        raw_score *= behavior_mult
        
        # Apply keyword stuffer penalty
        stuffer_penalty = keyword_stuffer_penalty(candidate)
        final_score = raw_score * stuffer_penalty
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            candidate, career_score, skills_score, title_score, final_score
        )
        
        return final_score, reasoning

    def _score_career_substance(self, candidate: dict) -> float:
        """Component 1: Career Substance (0.35 weight)."""
        # Sub-components
        production_ai_score = self._score_production_ai_evidence(candidate)
        industry_quality_score = self._score_industry_quality(candidate)
        company_quality_score = self._score_company_quality(candidate)
        tenure_stability_score = self._score_tenure_stability(candidate)
        
        # Average the sub-components
        return (
            0.35 * production_ai_score +
            0.25 * industry_quality_score +
            0.25 * company_quality_score +
            0.15 * tenure_stability_score
        )

    def _score_production_ai_evidence(self, candidate: dict) -> float:
        """1a: Production AI/ML system evidence."""
        career_history = candidate.get('career_history', [])
        
        score = 0.0
        text_to_scan = ''
        
        for role in career_history:
            text_to_scan += (role.get('title', '') + ' ' + 
                           role.get('description', '') + ' ').lower()
        
        # Count strong signals
        strong_count = 0
        for signal in self.STRONG_SIGNALS:
            if signal in text_to_scan:
                strong_count += 1
        
        # Count weak signals
        weak_count = 0
        for signal in self.WEAK_SIGNALS:
            if signal in text_to_scan:
                weak_count += 1
        
        score = min(1.0, (strong_count * 0.15 + weak_count * 0.05))
        
        return score

    def _score_industry_quality(self, candidate: dict) -> float:
        """1b: Industry quality scoring."""
        career_history = candidate.get('career_history', [])
        
        if not career_history:
            return 0.0
        
        industry_scores = []
        
        for idx, role in enumerate(career_history):
            industry = role.get('industry', '').lower()
            
            # Recency weight (most recent = higher)
            recency_weight = 2.718 ** (-0.3 * idx)  # exp(-0.3 * i)
            
            # Industry scoring
            if industry in ['ai/ml', 'ai', 'ml']:
                industry_score = 1.0
            elif any(ind in industry for ind in ['software', 'fintech', 'e-commerce', 
                                                 'food delivery', 'transportation', 'healthtech']):
                industry_score = 0.8
            elif 'it services' in industry:
                # Check if product or consulting
                company_size = role.get('company_size', 10001)
                if company_size < 1001:
                    industry_score = 0.5
                else:
                    industry_score = 0.1
            else:
                industry_score = 0.2
            
            industry_scores.append(industry_score * recency_weight)
        
        return min(1.0, sum(industry_scores) / len(career_history))

    def _score_company_quality(self, candidate: dict) -> float:
        """1c: Company quality (consulting firm detection)."""
        career_history = candidate.get('career_history', [])
        
        if not career_history:
            return 0.5
        
        # Check for consulting firm history
        consulting_months = 0
        total_months = 0
        most_recent_is_product = False
        
        for idx, role in enumerate(career_history):
            company_name = role.get('company_name', '').lower()
            duration = role.get('duration_months', 0)
            total_months += duration
            
            is_consulting = any(firm in company_name for firm in self.CONSULTING_FIRMS)
            
            if is_consulting:
                consulting_months += duration
            elif idx == 0:  # Most recent
                most_recent_is_product = True
        
        # Scoring logic
        if total_months == consulting_months:
            return 0.0  # All consulting = disqualified
        elif most_recent_is_product and consulting_months > 0:
            return 0.5  # Product role now, some consulting history
        elif consulting_months == 0:
            return 1.0  # All product companies
        else:
            # Mix
            return max(0.2, consulting_months / total_months)

    def _score_tenure_stability(self, candidate: dict) -> float:
        """1d: Tenure stability (penalize job hoppers)."""
        career_history = candidate.get('career_history', [])
        
        # Only non-current roles
        past_roles = [r for r in career_history[1:] if r.get('is_current') is False]
        
        if not past_roles:
            return 0.5
        
        total_months = sum(r.get('duration_months', 0) for r in past_roles)
        if total_months == 0:
            return 0.1
        
        avg_tenure = total_months / len(past_roles)
        
        if avg_tenure < 12:
            return 0.1
        elif avg_tenure < 18:
            return 0.4
        elif avg_tenure < 30:
            return 0.7
        else:
            return 1.0

    def _score_skills_depth(self, candidate: dict) -> float:
        """Component 2: Skills Depth (0.25 weight)."""
        skills = candidate.get('skills', [])
        
        if not skills:
            return 0.0
        
        # Check if any must-have or nice-have skills present
        must_have_found = False
        nice_have_found = False
        
        for skill in skills:
            skill_name = skill.get('name', '').lower()
            if any(mh in skill_name for mh in self.MUST_HAVE_SKILLS):
                must_have_found = True
            if any(nh in skill_name for nh in self.NICE_HAVE_SKILLS):
                nice_have_found = True
        
        # 2b: If no must-have AND no nice-have, score = 0
        if not must_have_found and not nice_have_found:
            return 0.0
        
        # 2a: Compute skill depth
        must_have_score = self._compute_skill_list_score(skills, self.MUST_HAVE_SKILLS, candidate)
        nice_have_score = self._compute_skill_list_score(skills, self.NICE_HAVE_SKILLS, candidate)
        
        skills_depth = 0.7 * must_have_score + 0.3 * nice_have_score
        
        return min(1.0, skills_depth)

    def _compute_skill_list_score(self, skills: List[dict], target_skills: set, candidate: dict) -> float:
        """Compute weighted score for a skill list."""
        if not target_skills:
            return 0.0
        
        total_score = 0.0
        matches = 0
        
        career_text = ' '.join([
            role.get('description', '') + ' ' + role.get('title', '')
            for role in candidate.get('career_history', [])
        ]).lower()
        
        for skill in skills:
            skill_name = skill.get('name', '').lower()
            
            # Check if this skill matches target
            matched = False
            for target in target_skills:
                if target in skill_name:
                    matched = True
                    break
            
            if matched:
                matches += 1
                
                # Weight by proficiency
                proficiency = skill.get('proficiency', 'intermediate').lower()
                prof_weight = {
                    'beginner': 0.3,
                    'intermediate': 0.6,
                    'advanced': 0.85,
                    'expert': 1.0
                }.get(proficiency, 0.5)
                
                # Weight by duration
                duration = skill.get('duration_months', 0)
                duration_weight = min(1.0, duration / 36)
                
                # Weight by endorsements
                endorsements = skill.get('endorsements', 0)
                endorsement_weight = min(1.0, endorsements / 20)
                
                # Cross-validate with career history
                trust_weight = 1.0 if skill_name in career_text else 0.5
                
                skill_score = prof_weight * duration_weight * endorsement_weight * trust_weight
                total_score += skill_score
        
        if matches == 0:
            return 0.0
        
        return total_score / len(target_skills)

    def _score_title_role_fit(self, candidate: dict) -> float:
        """Component 3: Title & Role Fit (0.20 weight)."""
        current_title = candidate.get('current_title', '')
        
        # 3a: Current title fit
        current_title_score = title_tier_score(current_title)
        
        # 3b: Career trajectory
        career_history = candidate.get('career_history', [])
        
        # Find best title in last 3 years
        best_recent_score = 0.0
        for role in career_history:
            # Simple recency check: if role is recent enough
            if role.get('duration_months', 0) > 0 or role.get('is_current'):
                role_title = role.get('title', '')
                role_score = title_tier_score(role_title)
                best_recent_score = max(best_recent_score, role_score)
        
        trajectory_score = 0.6 * best_recent_score + 0.4 * current_title_score
        
        return trajectory_score

    def _score_experience_calibration(self, candidate: dict) -> float:
        """Component 4: Experience Calibration (0.10 weight)."""
        yoe = candidate.get('years_of_experience', 0)
        return experience_score(yoe)

    def _score_location_logistics(self, candidate: dict) -> float:
        """Component 5: Location & Logistics (0.10 weight)."""
        location = candidate.get('location', '')
        willing_to_relocate = candidate.get('willing_to_relocate', False)
        notice_days = candidate.get('notice_period_days', 0)
        
        location_score_val = location_score(location, willing_to_relocate)
        notice_score_val = notice_period_score(notice_days)
        
        final_location_score = 0.65 * location_score_val + 0.35 * notice_score_val
        
        return final_location_score

    def _generate_reasoning(self, candidate: dict, career_score: float,
                          skills_score: float, title_score: float,
                          final_score: float) -> str:
        """Generate concise, fact-based reasoning."""
        current_title = candidate.get('current_title', '')
        yoe = candidate.get('years_of_experience', 0)
        location = candidate.get('location', '')
        
        # Extract key signals
        signals = []
        
        career_history = candidate.get('career_history', [])
        combined_text = ' '.join([
            role.get('title', '') + ' ' + role.get('description', '')
            for role in career_history
        ]).lower()
        
        # Check for strong signals
        if 'embedding' in combined_text or 'vector' in combined_text:
            signals.append('embedding/vector experience')
        if 'ranking' in combined_text or 'retrieval' in combined_text:
            signals.append('ranking systems')
        if 'recommendation' in combined_text:
            signals.append('recommendations')
        if 'pinecone' in combined_text or 'weaviate' in combined_text or 'qdrant' in combined_text:
            signals.append('vector DB expertise')
        if 'production' in combined_text or 'deployed' in combined_text:
            signals.append('production experience')
        if 'a/b test' in combined_text or 'ndcg' in combined_text or 'mrr' in combined_text:
            signals.append('evaluation frameworks')
        
        # Build reasoning
        if not signals:
            reasons = [f"{current_title} ({yoe:.0f}y exp)"]
        else:
            reasons = signals[:2]  # Top 2 signals
        
        # Add weakness if any
        if career_score < 0.5:
            reasons.append('limited production AI evidence')
        if skills_score < 0.3:
            reasons.append('limited required skills')
        
        reasoning = ', '.join(reasons)
        
        # Truncate to fit format
        if len(reasoning) > 150:
            reasoning = reasoning[:147] + '...'
        
        return reasoning
