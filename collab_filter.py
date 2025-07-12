import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborativeFilterEngine:
    """
    Collaborative filtering engine that works with the simplified data structure.
    Uses user-skill interactions and ratings for recommendations.
    """
    
    def __init__(self):
        self.users_df = None
        self.swaps_df = None
        self.user_skill_matrix = None
        self.user_similarities = None
        
    def load_data(self, users_df: pd.DataFrame, swaps_df: pd.DataFrame):
        """Load and prepare data for collaborative filtering."""
        logger.info("Loading data for collaborative filtering engine...")
        
        self.users_df = users_df.copy()
        self.swaps_df = swaps_df.copy()
        
        # Create user-skill matrix
        self._create_user_skill_matrix()
        
        # Calculate user similarities
        self._calculate_user_similarities()
        
        logger.info("Collaborative filtering engine loaded successfully")
    
    def _create_user_skill_matrix(self):
        """Create user-skill matrix from user data."""
        if self.users_df.empty:
            return
        
        # Create matrix with user_id as index and skills as columns
        # Use skill_level * rating as the interaction strength
        self.users_df['interaction_strength'] = self.users_df['skill_level'] * self.users_df['rating']
        
        self.user_skill_matrix = self.users_df.pivot_table(
            index='user_id', 
            columns='skills', 
            values='interaction_strength', 
            fill_value=0
        )
        
        logger.info("User-skill matrix created")
    
    def _calculate_user_similarities(self):
        """Calculate pairwise user similarities using cosine similarity."""
        if self.user_skill_matrix is None or self.user_skill_matrix.empty:
            return
        
        try:
            # Convert to numpy array for faster computation
            user_vectors = self.user_skill_matrix.values
            
            # Calculate cosine similarities
            similarities = cosine_similarity(user_vectors)
            
            # Store similarities with user IDs
            user_ids = self.user_skill_matrix.index.values
            self.user_similarities = {}
            
            for i, user_id in enumerate(user_ids):
                self.user_similarities[user_id] = {}
                for j, other_user_id in enumerate(user_ids):
                    if i != j:
                        self.user_similarities[user_id][other_user_id] = similarities[i, j]
            
            logger.info("User similarities calculated")
            
        except Exception as e:
            logger.error(f"Error calculating user similarities: {e}")
            self.user_similarities = {}
    
    def get_recommendations(self, user_id: int, n_recommendations: int = 5) -> List[Dict]:
        """Get collaborative filtering recommendations for a user."""
        if self.user_similarities is None or user_id not in self.user_similarities:
            return []
        
        try:
            # Get similar users
            similar_users = self._get_similar_users(user_id, n_similar=10)
            
            # Get skills that similar users have but target user doesn't
            user_skills = set(self._get_user_skills(user_id))
            recommendations = []
            
            for similar_user_id, similarity_score in similar_users:
                if similarity_score < 0.1:  # Skip users with very low similarity
                    continue
                
                similar_user_skills = self._get_user_skills(similar_user_id)
                
                for skill_info in similar_user_skills:
                    if skill_info['skill'] not in user_skills:
                        # Check if this skill is already recommended
                        existing_rec = next((r for r in recommendations if r['skill'] == skill_info['skill']), None)
                        
                        if existing_rec:
                            # Update with higher similarity score
                            if similarity_score > existing_rec['similarity_score']:
                                existing_rec['similarity_score'] = similarity_score
                                existing_rec['recommended_by'] = similar_user_id
                        else:
                            recommendations.append({
                                'skill': skill_info['skill'],
                                'similarity_score': similarity_score,
                                'recommended_by': similar_user_id,
                                'skill_level': skill_info['level'],
                                'skill_rating': skill_info['rating'],
                                'recommendation_type': 'collaborative'
                            })
            
            # Sort by similarity score and return top n
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Error getting collaborative recommendations for user {user_id}: {e}")
            return []
    
    def _get_similar_users(self, user_id: int, n_similar: int = 10) -> List[Tuple[int, float]]:
        """Get users similar to the target user."""
        if self.user_similarities is None or user_id not in self.user_similarities:
            return []
        
        try:
            # Get similarities for the user
            user_similarities = self.user_similarities[user_id]
            
            # Sort by similarity score
            similar_users = sorted(user_similarities.items(), key=lambda x: x[1], reverse=True)
            
            return similar_users[:n_similar]
            
        except Exception as e:
            logger.error(f"Error getting similar users for user {user_id}: {e}")
            return []
    
    def _get_user_skills(self, user_id: int) -> List[Dict]:
        """Get skills for a specific user."""
        user_data = self.users_df[self.users_df['user_id'] == user_id]
        
        if user_data.empty:
            return []
        
        skills = []
        for _, row in user_data.iterrows():
            skills.append({
                'skill': row['skills'],
                'level': row['skill_level'],
                'rating': row['rating'],
                'description': row['description']
            })
        
        return skills
    
    def get_user_learning_patterns(self, user_id: int) -> Dict:
        """Analyze user's learning patterns and preferences."""
        if self.swaps_df is None:
            return {}
        
        try:
            # Get user's learning history
            user_swaps = self.swaps_df[self.swaps_df['user_id_of_learner'] == user_id]
            
            if user_swaps.empty:
                return {
                    'total_sessions': 0,
                    'preferred_teachers': [],
                    'learning_duration': 0,
                    'active_sessions': 0
                }
            
            # Analyze learning patterns
            total_sessions = len(user_swaps)
            
            # Find preferred teachers (most frequent)
            teacher_counts = user_swaps['user_id_of_teacher'].value_counts()
            preferred_teachers = teacher_counts.head(3).to_dict()
            
            # Calculate average learning duration
            durations = []
            active_sessions = 0
            current_date = datetime.now().date()
            
            for _, swap in user_swaps.iterrows():
                try:
                    start_date = datetime.strptime(swap['starting_date_of_learning_or_teaching'], '%Y-%m-%d').date()
                    end_date = datetime.strptime(swap['ending_date_of_learning_or_teaching'], '%Y-%m-%d').date()
                    
                    duration = (end_date - start_date).days
                    durations.append(duration)
                    
                    # Check if session is active
                    if start_date <= current_date <= end_date:
                        active_sessions += 1
                        
                except:
                    continue
            
            avg_duration = np.mean(durations) if durations else 0
            
            return {
                'total_sessions': total_sessions,
                'preferred_teachers': preferred_teachers,
                'learning_duration': round(avg_duration, 1),
                'active_sessions': active_sessions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing learning patterns for user {user_id}: {e}")
            return {}
    
    def get_skill_popularity(self, skill_name: str) -> Dict:
        """Get popularity metrics for a specific skill."""
        if self.users_df is None:
            return {}
        
        try:
            skill_data = self.users_df[self.users_df['skills'] == skill_name]
            
            if skill_data.empty:
                return {}
            
            total_users = len(skill_data)
            avg_level = skill_data['skill_level'].mean()
            avg_rating = skill_data['rating'].mean()
            
            # Get difficulty level
            difficulty_levels = {
                'Beginner': skill_data[skill_data['skill_level'] <= 2].shape[0],
                'Intermediate': skill_data[(skill_data['skill_level'] > 2) & (skill_data['skill_level'] <= 4)].shape[0],
                'Advanced': skill_data[skill_data['skill_level'] > 4].shape[0]
            }
            
            return {
                'skill': skill_name,
                'total_users': total_users,
                'avg_level': round(avg_level, 2),
                'avg_rating': round(avg_rating, 2),
                'difficulty_distribution': difficulty_levels,
                'popularity_score': total_users * avg_rating
            }
            
        except Exception as e:
            logger.error(f"Error getting skill popularity for {skill_name}: {e}")
            return {}
    
    def get_recommendation_explanation(self, user_id: int, skill_name: str) -> str:
        """Generate explanation for why a skill is recommended to a user."""
        if self.user_similarities is None or user_id not in self.user_similarities:
            return "No explanation available"
        
        try:
            # Find similar users who have this skill
            similar_users = self._get_similar_users(user_id, n_similar=5)
            user_skills = set(self._get_user_skills(user_id))
            
            explanations = []
            for similar_user_id, similarity_score in similar_users:
                if similarity_score < 0.1:
                    continue
                
                similar_user_skills = self._get_user_skills(similar_user_id)
                for skill_info in similar_user_skills:
                    if skill_info['skill'] == skill_name and skill_info['skill'] not in user_skills:
                        explanations.append(
                            f"User {similar_user_id} (similarity: {similarity_score:.2f}) "
                            f"has this skill at level {skill_info['level']} with rating {skill_info['rating']}"
                        )
            
            if explanations:
                return f"Recommended because: {'; '.join(explanations[:2])}"
            else:
                return "Recommended based on skill popularity and user patterns"
                
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return "No explanation available"
    
    def get_stats(self) -> Dict:
        """Get statistics about the collaborative filtering engine."""
        if self.users_df is None or self.swaps_df is None:
            return {}
        
        total_users = self.users_df['user_id'].nunique()
        total_skills = self.users_df['skills'].nunique()
        total_swaps = len(self.swaps_df)
        
        avg_skill_level = self.users_df['skill_level'].mean()
        avg_rating = self.users_df['rating'].mean()
        
        # Calculate sparsity of user-skill matrix
        if self.user_skill_matrix is not None:
            total_possible_interactions = self.user_skill_matrix.shape[0] * self.user_skill_matrix.shape[1]
            actual_interactions = (self.user_skill_matrix != 0).sum().sum()
            sparsity = 1 - (actual_interactions / total_possible_interactions)
        else:
            sparsity = 0
        
        return {
            'total_users': total_users,
            'total_skills': total_skills,
            'total_swaps': total_swaps,
            'avg_skill_level': round(avg_skill_level, 2),
            'avg_rating': round(avg_rating, 2),
            'matrix_sparsity': round(sparsity, 3),
            'engine_type': 'collaborative'
        } 