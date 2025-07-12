import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from simple_recommendation_engine import SimpleRecommendationEngine

# Sample test data
@pytest.fixture
def sample_data():
    """Create sample data for testing."""
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

def test_engine_initialization():
    """Test that the engine initializes correctly."""
    engine = SimpleRecommendationEngine()
    assert engine.users_df is None
    assert engine.swaps_df is None
    assert engine.user_skill_matrix is None

def test_data_loading(sample_data):
    """Test that data loads correctly."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    
    engine.load_data(users_df, swaps_df)
    
    assert engine.users_df is not None
    assert engine.swaps_df is not None
    assert engine.user_skill_matrix is not None
    assert len(engine.users_df) == 10
    assert len(engine.swaps_df) == 10

def test_get_user_skills(sample_data):
    """Test getting user skills."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    user_skills = engine._get_user_skills(1)
    assert len(user_skills) == 2
    assert user_skills[0]['skill'] == 'Python Programming'
    assert user_skills[0]['level'] == 4
    assert user_skills[1]['skill'] == 'Data Analysis'
    assert user_skills[1]['level'] == 3

def test_get_seeking_skills(sample_data):
    """Test getting skills user is seeking."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    seeking_skills = engine._get_seeking_skills(1)
    assert len(seeking_skills) == 1
    assert 'Machine Learning' in seeking_skills

def test_get_skills_to_learn(sample_data):
    """Test getting skills to learn."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    skills_to_learn = engine._get_skills_to_learn(1, ['Machine Learning'], 3)
    assert isinstance(skills_to_learn, list)
    assert len(skills_to_learn) <= 3

def test_get_skills_to_offer(sample_data):
    """Test getting skills to offer."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    skills_to_offer = engine._get_skills_to_offer(1, 3)
    assert isinstance(skills_to_offer, list)
    assert len(skills_to_offer) <= 3

def test_get_learning_history(sample_data):
    """Test getting learning history."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    history = engine._get_learning_history(1)
    assert isinstance(history, list)
    assert len(history) == 2  # User 1 has 2 learning sessions

def test_is_learning_session_active():
    """Test active session detection."""
    engine = SimpleRecommendationEngine()
    
    # Test active session
    current_date = datetime.now().date()
    start_date = (current_date - timedelta(days=5)).strftime('%Y-%m-%d')
    end_date = (current_date + timedelta(days=5)).strftime('%Y-%m-%d')
    
    assert engine._is_learning_session_active(start_date, end_date) == True
    
    # Test inactive session (past)
    past_start = (current_date - timedelta(days=20)).strftime('%Y-%m-%d')
    past_end = (current_date - timedelta(days=10)).strftime('%Y-%m-%d')
    
    assert engine._is_learning_session_active(past_start, past_end) == False
    
    # Test inactive session (future)
    future_start = (current_date + timedelta(days=10)).strftime('%Y-%m-%d')
    future_end = (current_date + timedelta(days=20)).strftime('%Y-%m-%d')
    
    assert engine._is_learning_session_active(future_start, future_end) == False

def test_get_user_status(sample_data):
    """Test getting user status."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    status = engine.get_user_status(1)
    assert status in ['available', 'busy']

def test_get_recommendations(sample_data):
    """Test getting recommendations."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    recommendations = engine.get_recommendations(1, n_recommendations=5)
    
    # Check structure
    assert 'user_id' in recommendations
    assert 'user_swap_count' in recommendations
    assert 'recommendation_type' in recommendations
    assert 'skills_to_learn' in recommendations
    assert 'skills_to_offer' in recommendations
    assert 'current_skills' in recommendations
    assert 'seeking_skills' in recommendations
    assert 'learning_history' in recommendations
    assert 'current_status' in recommendations
    assert 'active_sessions' in recommendations
    assert 'weights' in recommendations
    assert 'timestamp' in recommendations
    
    # Check values
    assert recommendations['user_id'] == 1
    assert recommendations['recommendation_type'] == 'simple'
    assert isinstance(recommendations['skills_to_learn'], list)
    assert isinstance(recommendations['skills_to_offer'], list)
    assert isinstance(recommendations['current_skills'], list)
    assert isinstance(recommendations['seeking_skills'], list)
    assert isinstance(recommendations['learning_history'], list)
    assert recommendations['current_status'] in ['available', 'busy']
    assert isinstance(recommendations['active_sessions'], int)
    assert isinstance(recommendations['weights'], dict)

def test_get_stats(sample_data):
    """Test getting engine stats."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    stats = engine.get_stats()
    
    assert 'total_users' in stats
    assert 'total_skills' in stats
    assert 'total_swaps' in stats
    assert 'avg_skill_level' in stats
    assert 'avg_rating' in stats
    assert 'engine_type' in stats
    
    assert stats['total_users'] == 5  # Unique users
    assert stats['total_skills'] == 10  # Total skill entries
    assert stats['total_swaps'] == 10
    assert stats['engine_type'] == 'simple'

def test_empty_data():
    """Test engine behavior with empty data."""
    engine = SimpleRecommendationEngine()
    
    # Test with empty DataFrames
    empty_users = pd.DataFrame()
    empty_swaps = pd.DataFrame()
    
    engine.load_data(empty_users, empty_swaps)
    
    # Should handle empty data gracefully
    recommendations = engine.get_recommendations(1)
    assert recommendations['skills_to_learn'] == []
    assert recommendations['skills_to_offer'] == []
    assert recommendations['current_skills'] == []
    assert recommendations['seeking_skills'] == []

def test_non_existent_user(sample_data):
    """Test behavior with non-existent user."""
    users_df, swaps_df = sample_data
    engine = SimpleRecommendationEngine()
    engine.load_data(users_df, swaps_df)
    
    # Should handle non-existent user gracefully
    recommendations = engine.get_recommendations(999)
    assert recommendations['user_id'] == 999
    assert recommendations['skills_to_learn'] == []
    assert recommendations['skills_to_offer'] == []

if __name__ == "__main__":
    pytest.main([__file__]) 