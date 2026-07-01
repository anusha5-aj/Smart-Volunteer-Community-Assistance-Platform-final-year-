from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_match(volunteer_skills, event_skills):
    """
    Improved AI skill matching function that compares individual skills.
    
    Steps:
    1. Split skills into lists and normalize (lowercase, strip).
    2. Compare each event skill against all volunteer skills.
    3. Use TF-IDF (NGram 1,2) and Cosine Similarity for each pair.
    4. If similarity > 0.5, the skill is matched.
    5. Calculate percentage based on count of matched skills.
    """
    # 1. Normalize and split skills
    v_list = [s.strip().lower() for s in volunteer_skills.split(',') if s.strip()] if volunteer_skills else []
    e_list = [s.strip().lower() for s in event_skills.split(',') if s.strip()] if event_skills else []

    if not e_list:
        return {"match_percentage": 0.0, "matched_skills": [], "missing_skills": []}
    
    if not v_list:
        return {"match_percentage": 0.0, "matched_skills": [], "missing_skills": e_list}

    # 2. TF-IDF Configuration
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    
    matched_skills = []
    missing_skills = []

    # 3. Iterate through each event skill
    for e_skill in e_list:
        is_matched = False
        
        # 4. Compare with every volunteer skill
        for v_skill in v_list:
            # Quick exact check
            if e_skill == v_skill:
                is_matched = True
                break
                
            try:
                # Compute TF-IDF similarity for the pair
                tfidf_matrix = vectorizer.fit_transform([e_skill, v_skill])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                
                # Check threshold
                if similarity >= 0.5:
                    is_matched = True
                    break
            except Exception:
                # Handle cases where skills might be entirely stop words
                if e_skill in v_skill or v_skill in e_skill:
                    is_matched = True
                    break
        
        if is_matched:
            matched_skills.append(e_skill)
        else:
            missing_skills.append(e_skill)

    # 5. Calculate match percentage
    num_matched = len(matched_skills)
    total_event_skills = len(e_list)
    match_percentage = round((num_matched / total_event_skills) * 100, 2)

    return {
        "match_percentage": match_percentage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
    }

def calculate_skill_match(volunteer_skills, event_skills):
    """
    Central wrapper returning only the percentage for numerical comparisons.
    """
    result = calculate_match(volunteer_skills, event_skills)
    return result["match_percentage"]

# Example usage for testing
if __name__ == "__main__":
    v = "Teaching, Communication"
    e = "Teaching, Communication, English"
    
    print(f"Volunteer: {v}")
    print(f"Event Required: {e}")
    
    res = calculate_match(v, e)
    print(f"Match Score: {res['match_percentage']}%")
    print(f"Matched: {res['matched_skills']}")
    print(f"Missing: {res['missing_skills']}")
