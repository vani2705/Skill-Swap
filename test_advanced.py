import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from simple_recommendation_engine import SimpleRecommendationEngine
from faiss_engine import FAISSContentEngine
from collab_filter import CollaborativeFilterEngine

# Sample test data for advanced features
@pytest.fixture
def advanced_sample_data():
    """Create sample data for testing advanced features."""
    users_df = pd.DataFrame({
        'user_id': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        'skills': ['Python Programming', 'Data Analysis', 'Machine Learning', 'Deep Learning', 
                  'React Development', 'Node.js', 'UX Design', 'User Research', 'DevOps', 'Cloud Computing'],
        'skill_level': [4, 3, 5, 5, 4, 3, 5, 4, 5, 4],
        'description': [
            'Software developer passionate about Python and machine learning',
            'Software developer passionate about Python and machine learning',
            'Data scientist working with big data and analytics',
            'Data scientist working with big data and analytics',
            'Web developer specializing in React and Node.js',
            'Web developer specializing in React and Node.js',
            'UX designer with focus on user research and design thinking',
            'UX designer with focus on user research and design thinking',
            'DevOps engineer with cloud expertise',
            'DevOps engineer with cloud expertise'
        ],
        'rating': [4.5, 4.0, 4.8, 4.9, 4.2, 4.0, 4.5, 4.3, 4.7, 4.4],
        'feedback': [
            'Excellent course, very practical and well-structured',
            'Good content, helped me understand data analysis basics',
            'Fantastic course, very comprehensive and practical',
            'Amazing content, cutting-edge techniques',
            'Very good course, helped me build better React apps',
            'Good foundation for backend development',
            'Great course on user experience design',
            'Very practical research methods',
            'Comprehensive DevOps course',
            'Great cloud fundamentals'
        ],
        'status': ['available', 'available', 'available', 'available', 'available', 
                  'available', 'available', 'available', 'available', 'available'],
        'skill_user_is_seeking_for': ['Machine Learning', 'Machine Learning', 'Quantum Computing', 
                                     'Quantum Computing', 'Cloud Deployment', 'Cloud Deployment',
                                     'UI Design', 'UI Design', 'Kubernetes', 'Kubernetes']
    })
    
    swaps_df = pd.DataFrame({
        'user_id_of_learner': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        'user_id_of_teacher': [2, 8, 15, 8, 5, 12, 13, 13, 19, 12],
        'starting_date_of_learning_or_teaching': [
            '2024-01-15', '2024-02-10', '2024-01-20', '2024-02-05',
            '2024-01-25', '2024-02-15', '2024-01-30', '2024-02-20',
            '2024-02-01', '2024-02-25'
        ],
        'ending_date_of_learning_or_teaching': [
            '2024-03-15', '2024-04-10', '2024-03-20', '2024-04-05',
            '2024-03-25', '2024-04-15', '2024-03-30', '2024-04-20',
            '2024-04-01', '2024-04-25'
        ]
    })
    
    return users_df, swaps_df

def test_content_engine_initialization():
    """Test that the content engine initializes correctly."""
    engine = FAISSContentEngine()
    assert engine.users_df is None
    assert engine.swaps_df is None
    assert engine.tfidf_vectorizer is None
    assert engine.skill_vectors is None

def test_content_engine_data_loading(advanced_sample_data):
    """Test that content engine loads data correctly."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    
    engine.load_data(users_df, swaps_df)
    
    assert engine.users_df is not None
    assert engine.swaps_df is not None
    assert engine.skill_descriptions is not None
    assert len(engine.skill_descriptions) == 10

def test_content_based_recommendations(advanced_sample_data):
    """Test content-based recommendations."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    user_skills = ['Python Programming', 'Data Analysis']
    recommendations = engine.get_user_skill_recommendations(user_skills, 3)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 3
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'similarity_score' in rec
            assert 'recommendation_type' in rec
            assert rec['recommendation_type'] == 'content_based'

def test_similar_skills(advanced_sample_data):
    """Test finding similar skills."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    recommendations = engine.find_similar_skills('Python Programming', 3)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 3
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'similarity_score' in rec
            assert 'difficulty' in rec
            assert 'recommendation_type' in rec
            assert rec['recommendation_type'] == 'similar_skills'

def test_skills_by_difficulty(advanced_sample_data):
    """Test filtering skills by difficulty."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    recommendations = engine.get_skills_by_difficulty('Intermediate', None, 5)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'difficulty' in rec
            assert rec['difficulty'] == 'Intermediate'

def test_skills_by_category(advanced_sample_data):
    """Test filtering skills by category."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    recommendations = engine.get_skills_by_category('Programming', None, 5)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'category' in rec
            assert rec['category'] == 'Programming'

def test_keyword_search(advanced_sample_data):
    """Test keyword search functionality."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    keywords = ['python', 'programming']
    recommendations = engine.find_skills_by_keywords(keywords, None, 5)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 5
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'keyword_match_score' in rec
            assert 'recommendation_type' in rec
            assert rec['recommendation_type'] == 'keyword_search'

def test_collab_engine_initialization():
    """Test that the collaborative engine initializes correctly."""
    engine = CollaborativeFilterEngine()
    assert engine.users_df is None
    assert engine.swaps_df is None
    assert engine.user_skill_matrix is None
    assert engine.user_similarities is None

def test_collab_engine_data_loading(advanced_sample_data):
    """Test that collaborative engine loads data correctly."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    
    engine.load_data(users_df, swaps_df)
    
    assert engine.users_df is not None
    assert engine.swaps_df is not None
    assert engine.user_skill_matrix is not None
    assert engine.user_similarities is not None

def test_collaborative_recommendations(advanced_sample_data):
    """Test collaborative filtering recommendations."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    recommendations = engine.get_recommendations(1, 3)
    
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 3
    
    if recommendations:
        for rec in recommendations:
            assert 'skill' in rec
            assert 'similarity_score' in rec
            assert 'recommended_by' in rec
            assert 'recommendation_type' in rec
            assert rec['recommendation_type'] == 'collaborative'

def test_similar_users(advanced_sample_data):
    """Test finding similar users."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    similar_users = engine._get_similar_users(1, 5)
    
    assert isinstance(similar_users, list)
    assert len(similar_users) <= 5
    
    if similar_users:
        for user_id, similarity in similar_users:
            assert isinstance(user_id, int)
            assert isinstance(similarity, float)
            assert 0 <= similarity <= 1

def test_learning_patterns(advanced_sample_data):
    """Test learning pattern analysis."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    patterns = engine.get_user_learning_patterns(1)
    
    assert isinstance(patterns, dict)
    assert 'total_sessions' in patterns
    assert 'preferred_teachers' in patterns
    assert 'learning_duration' in patterns
    assert 'active_sessions' in patterns

def test_skill_popularity(advanced_sample_data):
    """Test skill popularity metrics."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    popularity = engine.get_skill_popularity('Python Programming')
    
    assert isinstance(popularity, dict)
    assert 'skill' in popularity
    assert 'total_users' in popularity
    assert 'avg_level' in popularity
    assert 'avg_rating' in popularity
    assert 'popularity_score' in popularity

def test_recommendation_explanation(advanced_sample_data):
    """Test recommendation explanation generation."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    explanation = engine.get_recommendation_explanation(1, 'Machine Learning')
    
    assert isinstance(explanation, str)
    assert len(explanation) > 0

def test_content_engine_stats(advanced_sample_data):
    """Test content engine statistics."""
    users_df, swaps_df = advanced_sample_data
    engine = FAISSContentEngine()
    engine.load_data(users_df, swaps_df)
    
    stats = engine.get_stats()
    
    assert 'total_skills' in stats
    assert 'avg_rating' in stats
    assert 'avg_level' in stats
    assert 'difficulty_distribution' in stats
    assert 'engine_type' in stats
    assert stats['engine_type'] == 'content_based'

def test_collab_engine_stats(advanced_sample_data):
    """Test collaborative engine statistics."""
    users_df, swaps_df = advanced_sample_data
    engine = CollaborativeFilterEngine()
    engine.load_data(users_df, swaps_df)
    
    stats = engine.get_stats()
    
    assert 'total_users' in stats
    assert 'total_skills' in stats
    assert 'total_swaps' in stats
    assert 'avg_skill_level' in stats
    assert 'avg_rating' in stats
    assert 'matrix_sparsity' in stats
    assert 'engine_type' in stats
    assert stats['engine_type'] == 'collaborative'

def test_difficulty_classification():
    """Test skill difficulty classification."""
    engine = FAISSContentEngine()
    
    # Test different skill difficulties
    assert engine._get_skill_difficulty('Python Programming') == 'Intermediate'
    assert engine._get_skill_difficulty('Machine Learning') == 'Advanced'
    assert engine._get_skill_difficulty('Git') == 'Beginner'
    assert engine._get_skill_difficulty('Quantum Computing') == 'Expert'

def test_category_classification():
    """Test skill category classification."""
    engine = FAISSContentEngine()
    
    # Test different skill categories
    assert engine._get_skill_category('Python Programming') == 'Programming'
    assert engine._get_skill_category('UX Design') == 'Design'
    assert engine._get_skill_category('Machine Learning') == 'Data'
    assert engine._get_skill_category('AWS') == 'Cloud'

def test_empty_data_handling():
    """Test engine behavior with empty data."""
    # Test content engine
    content_engine = FAISSContentEngine()
    empty_users = pd.DataFrame()
    empty_swaps = pd.DataFrame()
    
    content_engine.load_data(empty_users, empty_swaps)
    recommendations = content_engine.get_user_skill_recommendations(['Python'], 5)
    assert recommendations == []
    
    # Test collaborative engine
    collab_engine = CollaborativeFilterEngine()
    collab_engine.load_data(empty_users, empty_swaps)
    recommendations = collab_engine.get_recommendations(1, 5)
    assert recommendations == []

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 