import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleRecommendationEngine:
    """
    Simplified recommendation engine that works with users.csv and swaps.csv only.
    Uses skill levels, ratings, and learning history for recommendations.
    """
    
    def __init__(self):
        self.users_df = None
        self.swaps_df = None
        self.user_skill_matrix = None
        
    def load_data(self, users_df: pd.DataFrame, swaps_df: pd.DataFrame):
        """Load and prepare data for recommendations."""
        logger.info("Loading data for simple recommendation engine...")
        
        self.users_df = users_df.copy()
        self.swaps_df = swaps_df.copy()
        
        # Create user-skill matrix from user data
        self._create_user_skill_matrix()
        
        logger.info("Simple recommendation engine loaded successfully")
        
    def _create_user_skill_matrix(self):
        """Create user-skill matrix from user data."""
        if self.users_df.empty:
            return
            
        # Create matrix with user_id as index and skills as columns
        # Use skill_level as the value
        self.user_skill_matrix = self.users_df.pivot_table(
            index='user_id', 
            columns='skills', 
            values='skill_level', 
            fill_value=0
        )
        
        logger.info("User-skill matrix created")
    
    def get_recommendations(self, user_id: int, n_recommendations: int = 5) -> Dict:
        """Get recommendations for a user based on their skills and learning history."""
        try:
            if self.users_df is None or self.swaps_df is None:
                return self._get_empty_recommendations(user_id)
            
            # Get user's current skills
            user_skills = self._get_user_skills(user_id)
            
            # Get skills user is seeking
            seeking_skills = self._get_seeking_skills(user_id)
            
            # Get skills to learn (based on what user is seeking)
            skills_to_learn = self._get_skills_to_learn(user_id, seeking_skills, n_recommendations)
            
            # Get skills to offer (based on user's high-level skills)
            skills_to_offer = self._get_skills_to_offer(user_id, n_recommendations)
            
            # Get learning history
            learning_history = self._get_learning_history(user_id)
            
            # Get current user status
            current_status = self.get_user_status(user_id)
            
            return {
                'user_id': user_id,
                'user_swap_count': len(learning_history),
                'recommendation_type': 'simple',
                'skills_to_learn': skills_to_learn,
                'skills_to_offer': skills_to_offer,
                'current_skills': user_skills,
                'seeking_skills': seeking_skills,
                'learning_history': learning_history,
                'current_status': current_status,
                'active_sessions': len([h for h in learning_history if h.get('is_active', False)]),
                'weights': {
                    'skill_level': 0.4,
                    'rating': 0.3,
                    'popularity': 0.2,
                    'recency': 0.1
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            return self._get_empty_recommendations(user_id)
    
    def _get_user_skills(self, user_id: int) -> List[Dict]:
        """Get user's current skills with levels."""
        user_data = self.users_df[self.users_df['user_id'] == user_id]
        
        if user_data.empty:
            return []
        
        skills = []
        for _, row in user_data.iterrows():
            skills.append({
                'skill': row['skills'],
                'level': row['skill_level'],
                'rating': row['rating'],
                'description': row['description'],
                'status': row['status']
            })
        
        return skills
    
    def _get_seeking_skills(self, user_id: int) -> List[str]:
        """Get skills the user is seeking to learn."""
        user_data = self.users_df[self.users_df['user_id'] == user_id]
        
        if user_data.empty:
            return []
        
        seeking_skills = []
        for _, row in user_data.iterrows():
            if pd.notna(row['skill_user_is_seeking_for']):
                seeking_skills.append(row['skill_user_is_seeking_for'])
        
        return list(set(seeking_skills))  # Remove duplicates
    
    def _get_skills_to_learn(self, user_id: int, seeking_skills: List[str], n_recommendations: int) -> List[Dict]:
        """Get skills the user should learn based on what they're seeking."""
        if not seeking_skills:
            # If no specific seeking skills, recommend popular skills user doesn't have
            return self._get_popular_skills_to_learn(user_id, n_recommendations)
        
        recommendations = []
        user_skills = set([skill['skill'] for skill in self._get_user_skills(user_id)])
        
        for seeking_skill in seeking_skills:
            if seeking_skill not in user_skills:
                # Find users who have this skill at high level
                skilled_users = self.users_df[
                    (self.users_df['skills'] == seeking_skill) & 
                    (self.users_df['skill_level'] >= 4)
                ]
                
                if not skilled_users.empty:
                    best_user = skilled_users.loc[skilled_users['skill_level'].idxmax()]
                    recommendations.append({
                        'skill': seeking_skill,
                        'recommended_by': best_user['user_id'],
                        'teacher_rating': best_user['rating'],
                        'teacher_level': best_user['skill_level'],
                        'confidence': 0.9,
                        'reason': f"Based on your interest in {seeking_skill}"
                    })
        
        # Sort by confidence and return top n
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        return recommendations[:n_recommendations]
    
    def _get_popular_skills_to_learn(self, user_id: int, n_recommendations: int) -> List[Dict]:
        """Get popular skills that user doesn't have."""
        user_skills = set([skill['skill'] for skill in self._get_user_skills(user_id)])
        
        # Get all skills and their popularity
        skill_popularity = self.users_df.groupby('skills').agg({
            'skill_level': 'mean',
            'rating': 'mean',
            'user_id': 'count'
        }).reset_index()
        
        # Filter out skills user already has
        available_skills = skill_popularity[~skill_popularity['skills'].isin(user_skills)]
        
        if available_skills.empty:
            return []
        
        # Sort by popularity (count) and rating
        available_skills['popularity_score'] = (
            available_skills['user_id'] * 0.6 + 
            available_skills['rating'] * 0.4
        )
        
        top_skills = available_skills.nlargest(n_recommendations, 'popularity_score')
        
        recommendations = []
        for _, skill in top_skills.iterrows():
            recommendations.append({
                'skill': skill['skills'],
                'popularity': int(skill['user_id']),
                'avg_rating': round(skill['rating'], 2),
                'avg_level': round(skill['skill_level'], 1),
                'confidence': 0.7,
                'reason': "Popular skill with high ratings"
            })
        
        return recommendations
    
    def _get_skills_to_offer(self, user_id: int, n_recommendations: int) -> List[Dict]:
        """Get skills the user can offer to teach."""
        user_skills = self._get_user_skills(user_id)
        
        # Filter skills with high level (>= 4) and good rating (>= 4.0)
        teachable_skills = [
            skill for skill in user_skills 
            if skill['level'] >= 4 and skill['rating'] >= 4.0
        ]
        
        # Sort by level and rating
        teachable_skills.sort(key=lambda x: (x['level'], x['rating']), reverse=True)
        
        recommendations = []
        for skill in teachable_skills[:n_recommendations]:
            recommendations.append({
                'skill': skill['skill'],
                'level': skill['level'],
                'rating': skill['rating'],
                'description': skill['description'],
                'confidence': min(skill['level'] / 5.0, 1.0),
                'reason': f"High skill level ({skill['level']}/5) with good rating ({skill['rating']})"
            })
        
        return recommendations
    
    def _get_learning_history(self, user_id: int) -> List[Dict]:
        """Get user's learning history from swaps."""
        user_swaps = self.swaps_df[self.swaps_df['user_id_of_learner'] == user_id]
        
        history = []
        for _, swap in user_swaps.iterrows():
            # Find the teacher's skill info
            teacher_skills = self.users_df[
                (self.users_df['user_id'] == swap['user_id_of_teacher']) &
                (self.users_df['skills'].isin(self._get_seeking_skills(user_id)))
            ]
            
            if not teacher_skills.empty:
                skill_info = teacher_skills.iloc[0]
                history.append({
                    'teacher_id': swap['user_id_of_teacher'],
                    'skill': skill_info['skills'],
                    'start_date': swap['starting_date_of_learning_or_teaching'],
                    'end_date': swap['ending_date_of_learning_or_teaching'],
                    'teacher_level': skill_info['skill_level'],
                    'teacher_rating': skill_info['rating'],
                    'is_active': self._is_learning_session_active(swap['starting_date_of_learning_or_teaching'], 
                                                                 swap['ending_date_of_learning_or_teaching'])
                })
        
        return history
    
    def _is_learning_session_active(self, start_date: str, end_date: str) -> bool:
        """Check if a learning session is currently active."""
        try:
            from datetime import datetime
            current_date = datetime.now().date()
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            return start <= current_date <= end
        except:
            return False
    
    def get_user_status(self, user_id: int) -> str:
        """Get current user status based on active learning sessions."""
        user_swaps = self.swaps_df[
            (self.swaps_df['user_id_of_learner'] == user_id) |
            (self.swaps_df['user_id_of_teacher'] == user_id)
        ]
        
        active_sessions = 0
        for _, swap in user_swaps.iterrows():
            if self._is_learning_session_active(swap['starting_date_of_learning_or_teaching'], 
                                              swap['ending_date_of_learning_or_teaching']):
                active_sessions += 1
        
        if active_sessions > 0:
            return "busy"
        else:
            return "available"
    
    def _get_empty_recommendations(self, user_id: int) -> Dict:
        """Return empty recommendations when data is not available."""
        return {
            'user_id': user_id,
            'user_swap_count': 0,
            'recommendation_type': 'simple',
            'skills_to_learn': [],
            'skills_to_offer': [],
            'current_skills': [],
            'seeking_skills': [],
            'learning_history': [],
            'weights': {
                'skill_level': 0.4,
                'rating': 0.3,
                'popularity': 0.2,
                'recency': 0.1
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        """Get statistics about the recommendation system."""
        if self.users_df is None or self.swaps_df is None:
            return {}
        
        total_users = self.users_df['user_id'].nunique()
        total_skills = self.users_df['skills'].nunique()
        total_swaps = len(self.swaps_df)
        
        avg_skill_level = self.users_df['skill_level'].mean()
        avg_rating = self.users_df['rating'].mean()
        
        return {
            'total_users': total_users,
            'total_skills': total_skills,
            'total_swaps': total_swaps,
            'avg_skill_level': round(avg_skill_level, 2),
            'avg_rating': round(avg_rating, 2),
            'engine_type': 'simple'
        } 