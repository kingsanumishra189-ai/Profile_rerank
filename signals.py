"""
Behavioral Signals Module
Implements behavioral multiplier and keyword stuffer penalty detection.
"""

import re
from datetime import datetime, timedelta


def behavioral_multiplier(candidate: dict) -> float:
    """
    Compute behavioral availability multiplier.
    Reduces score for unavailable/unresponsive candidates.
    
    Args:
        candidate: Candidate data dictionary
        
    Returns:
        Multiplier in range [0.0, 1.0]
    """
    base_multiplier = 1.0
    
    # Recruiter response rate penalty
    response_rate = candidate.get('recruiter_response_rate', 0.5)
    response_rate = max(0.0, min(1.0, response_rate))  # Clamp to [0, 1]
    
    if response_rate < 0.2:
        base_multiplier *= 0.3  # 70% penalty for very low response
    elif response_rate < 0.4:
        base_multiplier *= 0.6  # 40% penalty for low response
    elif response_rate < 0.6:
        base_multiplier *= 0.8  # 20% penalty for moderate response
    
    # Last active date penalty
    last_active = candidate.get('last_active_date')
    if last_active:
        try:
            # Handle both string and datetime formats
            if isinstance(last_active, str):
                last_active_date = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
            else:
                last_active_date = last_active
            
            days_inactive = (datetime.now(last_active_date.tzinfo or datetime.now().astimezone().tzinfo) - last_active_date).days
            
            if days_inactive > 180:  # 6+ months inactive
                base_multiplier *= 0.4
            elif days_inactive > 90:  # 3+ months inactive
                base_multiplier *= 0.65
            elif days_inactive > 30:  # 1+ month inactive
                base_multiplier *= 0.85
        except (ValueError, TypeError):
            pass  # If date parsing fails, apply no penalty
    
    # Notice period penalty (longer notice = less available)
    notice_days = candidate.get('notice_period_days', 0)
    
    if notice_days > 90:
        base_multiplier *= 0.85
    elif notice_days > 60:
        base_multiplier *= 0.9
    
    return max(0.1, base_multiplier)  # Floor at 0.1


def keyword_stuffer_penalty(candidate: dict) -> float:
    """
    Detect keyword stuffers: candidates with many AI keywords in skills
    but weak career evidence.
    
    Args:
        candidate: Candidate data dictionary
        
    Returns:
        Penalty multiplier in range [0.0, 1.0]
    """
    AI_KEYWORDS = {
        'embedding', 'vector', 'retrieval', 'ranking', 'recommendation',
        'semantic', 'search', 'neural', 'deep learning', 'machine learning',
        'nlp', 'llm', 'gpt', 'bert', 'transformer', 'rag', 'fine-tun',
        'lora', 'pinecone', 'weaviate', 'qdrant', 'milvus', 'faiss',
        'langchain', 'openai', 'inference', 'model', 'pytorch', 'tensorflow'
    }
    
    skills = candidate.get('skills', [])
    career_history = candidate.get('career_history', [])
    
    # Count AI keywords in skills list
    ai_skill_count = 0
    for skill in skills:
        skill_name = skill.get('name', '').lower()
        if any(keyword in skill_name for keyword in AI_KEYWORDS):
            ai_skill_count += 1
    
    # Count strong career signals in descriptions
    career_signals = 0
    STRONG_CAREER_SIGNALS = {
        'built', 'deployed', 'productionized', 'production', 'shipped',
        'architected', 'designed', 'implemented', 'optimized', 'scaled',
        'led', 'managed', 'developed', 'created', 'launched'
    }
    
    combined_descriptions = ' '.join([
        role.get('description', '').lower() + ' ' + role.get('title', '').lower()
        for role in career_history
    ])
    
    for signal in STRONG_CAREER_SIGNALS:
        if signal in combined_descriptions:
            career_signals += 1
    
    # Also count substantive technical keywords in career descriptions
    for keyword in ['embedding', 'vector', 'retrieval', 'ranking', 'recommendation',
                    'semantic search', 'neural', 'a/b test', 'ndcg', 'mrr']:
        if keyword in combined_descriptions:
            career_signals += 1
    
    # Penalty logic
    # Many AI skills but few career signals = keyword stuffer
    if ai_skill_count > 8 and career_signals < 3:
        return 0.3  # 70% penalty
    elif ai_skill_count > 6 and career_signals < 2:
        return 0.5  # 50% penalty
    elif ai_skill_count > 10 and career_signals < 4:
        return 0.4  # 60% penalty
    
    return 1.0  # No penalty


def title_tier_score(title: str) -> float:
    """
    Score a title based on fit tier.
    
    Args:
        title: Job title string
        
    Returns:
        Score in [0.0, 1.0]
    """
    title_lower = title.lower()
    
    # TIER 1 - Perfect fit (1.0)
    tier_1_keywords = [
        'ml engineer', 'machine learning engineer', 'ai engineer',
        'applied scientist', 'research engineer', 'nlp engineer',
        'search engineer', 'ranking engineer', 'recommendation engineer',
        'senior machine learning', 'staff ml', 'principal ml',
        'applied ml', 'deep learning engineer', 'ml research'
    ]
    
    for keyword in tier_1_keywords:
        if keyword in title_lower:
            return 1.0
    
    # TIER 2 - Strong fit (0.75)
    tier_2_keywords = [
        'data scientist', 'senior data scientist', 'lead data scientist',
        'software engineer', 'senior software engineer', 'backend engineer',
        'senior backend engineer', 'full stack engineer', 'platform engineer',
        'tech lead', 'engineering lead', 'senior engineer', 'ml specialist'
    ]
    
    for keyword in tier_2_keywords:
        if keyword in title_lower:
            return 0.75
    
    # TIER 3 - Moderate fit (0.45)
    tier_3_keywords = [
        'data engineer', 'cloud engineer', 'devops engineer',
        'infrastructure engineer', 'java developer', '.net developer',
        'mobile developer', 'frontend engineer', 'qa engineer', 'sdet',
        'solutions architect', 'database engineer'
    ]
    
    for keyword in tier_3_keywords:
        if keyword in title_lower:
            return 0.45
    
    # TIER 4 - Wrong domain (0.1)
    tier_4_keywords = [
        'hr manager', 'accountant', 'marketing manager', 'sales executive',
        'graphic designer', 'content writer', 'operations manager',
        'civil engineer', 'mechanical engineer', 'customer support',
        'business analyst', 'project manager', 'scrum master',
        'product manager', 'consultant', 'analyst'
    ]
    
    for keyword in tier_4_keywords:
        if keyword in title_lower:
            return 0.1
    
    # Default - unknown but possibly technical
    return 0.3


def experience_score(years_of_experience: float) -> float:
    """
    Score years of experience against target range (5-9 years, 4-10 acceptable).
    
    Args:
        years_of_experience: Float representing years
        
    Returns:
        Score in [0.0, 1.0]
    """
    # Target: 5-9 years (sweet spot)
    if 5 <= years_of_experience <= 9:
        return 1.0
    
    # Acceptable: 4-10 years
    if 4 <= years_of_experience <= 10:
        return 0.9
    
    # Close: 3-4 or 10-12 years
    if 3 <= years_of_experience < 4 or 10 < years_of_experience <= 12:
        return 0.7
    
    # Junior: < 3 years
    if years_of_experience < 3:
        return 0.4
    
    # Very senior: > 12 years (may be overqualified or slowing down)
    if years_of_experience > 12:
        return 0.6
    
    return 0.0


def notice_period_score(notice_days: int) -> float:
    """
    Score notice period (lower is better - candidate available sooner).
    
    Args:
        notice_days: Notice period in days
        
    Returns:
        Score in [0.0, 1.0]
    """
    if notice_days <= 0:
        return 1.0
    elif notice_days <= 7:
        return 0.95
    elif notice_days <= 14:
        return 0.9
    elif notice_days <= 30:
        return 0.8
    elif notice_days <= 60:
        return 0.6
    elif notice_days <= 90:
        return 0.4
    else:
        return 0.2


def location_score(location: str, willing_to_relocate: bool) -> float:
    """
    Score location fit for the role (Pune/Noida/Hyderabad/Mumbai preferred).
    
    Args:
        location: Candidate's location string
        willing_to_relocate: Whether candidate willing to relocate
        
    Returns:
        Score in [0.0, 1.0]
    """
    location_lower = location.lower() if location else ''
    
    # Preferred locations
    preferred_locations = ['pune', 'noida', 'hyderabad', 'mumbai', 'delhi', 'ncr']
    if any(loc in location_lower for loc in preferred_locations):
        return 1.0
    
    # Acceptable Indian cities
    acceptable_cities = [
        'bangalore', 'bengaluru', 'delhi', 'gurugram', 'gurgaon',
        'kolkata', 'chennai', 'ahmedabad', 'jaipur', 'lucknow'
    ]
    if any(city in location_lower for city in acceptable_cities):
        return 0.85
    
    # Other Indian cities
    if any(country in location_lower for country in ['india', 'indian']):
        if willing_to_relocate:
            return 0.65
        return 0.70
    
    # International
    international_countries = ['usa', 'uk', 'canada', 'australia', 'singapore', 'germany']
    if any(country in location_lower for country in international_countries):
        if willing_to_relocate:
            return 0.40
        return 0.05
    
    # Other international
    if willing_to_relocate:
        return 0.40
    return 0.05
