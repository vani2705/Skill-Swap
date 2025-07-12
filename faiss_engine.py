import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FAISSContentEngine:
    """
    Enhanced content-based filtering engine using TF-IDF and semantic understanding.
    Works with the simplified data structure (users.csv and swaps.csv).
    """
    
    def __init__(self):
        self.users_df = None
        self.swaps_df = None
        self.tfidf_vectorizer = None
        self.skill_vectors = None
        self.skill_descriptions = None
        
    def load_data(self, users_df: pd.DataFrame, swaps_df: pd.DataFrame):
        """Load and prepare data for content-based filtering."""
        logger.info("Loading data for FAISS content engine...")
        
        self.users_df = users_df.copy()
        self.swaps_df = swaps_df.copy()
        
        # Create enhanced text representations for skills
        self._create_skill_descriptions()
        
        # Initialize TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=2000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            strip_accents='unicode'
        )
        
        # Create TF-IDF vectors for skills
        if not self.skill_descriptions.empty:
            self.skill_vectors = self.tfidf_vectorizer.fit_transform(
                self.skill_descriptions['text_for_vectorization']
            )
            logger.info("FAISS content engine loaded successfully")
        else:
            logger.warning("No skill descriptions available for content engine")
    
    def _create_skill_descriptions(self):
        """Create enhanced skill descriptions for vectorization."""
        if self.users_df.empty:
            self.skill_descriptions = pd.DataFrame()
            return
        
        # Group skills and create enhanced descriptions
        skill_groups = self.users_df.groupby('skills').agg({
            'description': lambda x: ' '.join(x.unique()),
            'skill_level': 'mean',
            'rating': 'mean',
            'feedback': lambda x: ' '.join(x.unique()),
            'skill_user_is_seeking_for': lambda x: ' '.join(x.dropna().unique())
        }).reset_index()
        
        # Create enhanced text for vectorization
        skill_groups['text_for_vectorization'] = (
            skill_groups['skills'] + ' ' + 
            skill_groups['description'].fillna('') + ' ' + 
            skill_groups['feedback'].fillna('') + ' ' +
            skill_groups['skill_user_is_seeking_for'].fillna('')
        )
        
        self.skill_descriptions = skill_groups
        logger.info(f"Created descriptions for {len(skill_groups)} unique skills")
    
    def get_user_skill_recommendations(self, user_skills: List[str], n_recommendations: int = 5) -> List[Dict]:
        """Get content-based recommendations based on user's current skills."""
        if self.skill_vectors is None or self.skill_descriptions.empty:
            return []
        
        try:
            # Create user skill vector
            user_skill_text = ' '.join(user_skills)
            user_vector = self.tfidf_vectorizer.transform([user_skill_text])
            
            # Calculate similarities with all skills
            similarities = cosine_similarity(user_vector, self.skill_vectors).flatten()
            
            # Get top similar skills
            top_indices = np.argsort(similarities)[::-1][:n_recommendations]
            
            recommendations = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only include skills with some similarity
                    skill_info = self.skill_descriptions.iloc[idx]
                    recommendations.append({
                        'skill': skill_info['skills'],
                        'similarity_score': float(similarities[idx]),
                        'avg_level': round(skill_info['skill_level'], 1),
                        'avg_rating': round(skill_info['rating'], 2),
                        'description': skill_info['description'],
                        'recommendation_type': 'content_based'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting content-based recommendations: {e}")
            return []
    
    def find_similar_skills(self, skill_name: str, n_recommendations: int = 5, 
                           difficulty_filter: Optional[str] = None) -> List[Dict]:
        """Find skills similar to a given skill using content-based filtering."""
        if self.skill_vectors is None or self.skill_descriptions.empty:
            return []
        
        try:
            # Find the skill in our descriptions
            skill_mask = self.skill_descriptions['skills'] == skill_name
            if not skill_mask.any():
                return []
            
            skill_idx = skill_mask.idxmax()
            skill_vector = self.skill_vectors[skill_idx:skill_idx+1]
            
            # Calculate similarities with all other skills
            similarities = cosine_similarity(skill_vector, self.skill_vectors).flatten()
            
            # Filter by difficulty if specified
            if difficulty_filter:
                difficulty_levels = self._get_difficulty_levels()
                filtered_indices = [
                    i for i in range(len(self.skill_descriptions))
                    if self._get_skill_difficulty(self.skill_descriptions.iloc[i]['skills']) == difficulty_filter
                ]
            else:
                filtered_indices = list(range(len(self.skill_descriptions)))
            
            # Get top similar skills (excluding the skill itself)
            similar_scores = [(i, similarities[i]) for i in filtered_indices if i != skill_idx]
            similar_scores.sort(key=lambda x: x[1], reverse=True)
            
            recommendations = []
            for idx, score in similar_scores[:n_recommendations]:
                if score > 0:  # Only include skills with some similarity
                    skill_info = self.skill_descriptions.iloc[idx]
                    recommendations.append({
                        'skill': skill_info['skills'],
                        'similarity_score': float(score),
                        'avg_level': round(skill_info['skill_level'], 1),
                        'avg_rating': round(skill_info['rating'], 2),
                        'description': skill_info['description'],
                        'difficulty': self._get_skill_difficulty(skill_info['skills']),
                        'recommendation_type': 'similar_skills'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error finding similar skills: {e}")
            return []
    
    def get_skills_by_difficulty(self, difficulty_level: str, category: Optional[str] = None,
                                n_recommendations: int = 10) -> List[Dict]:
        """Get skills filtered by difficulty level and optionally by category."""
        if self.skill_descriptions.empty:
            return []
        
        try:
            # Filter skills by difficulty
            difficulty_levels = self._get_difficulty_levels()
            filtered_skills = []
            
            for _, skill_info in self.skill_descriptions.iterrows():
                skill_difficulty = self._get_skill_difficulty(skill_info['skills'])
                
                if skill_difficulty == difficulty_level:
                    # Additional category filter if specified
                    if category and not self._skill_matches_category(skill_info['skills'], category):
                        continue
                    
                    filtered_skills.append({
                        'skill': skill_info['skills'],
                        'avg_level': round(skill_info['skill_level'], 1),
                        'avg_rating': round(skill_info['rating'], 2),
                        'description': skill_info['description'],
                        'difficulty': skill_difficulty,
                        'category': self._get_skill_category(skill_info['skills']),
                        'recommendation_type': 'difficulty_based'
                    })
            
            # Sort by rating and return top n
            filtered_skills.sort(key=lambda x: x['avg_rating'], reverse=True)
            return filtered_skills[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Error getting skills by difficulty: {e}")
            return []
    
    def get_skills_by_category(self, category: str, difficulty_level: Optional[str] = None,
                              n_recommendations: int = 10) -> List[Dict]:
        """Get skills filtered by category and optionally by difficulty level."""
        if self.skill_descriptions.empty:
            return []
        
        try:
            filtered_skills = []
            
            for _, skill_info in self.skill_descriptions.iterrows():
                skill_category = self._get_skill_category(skill_info['skills'])
                
                if skill_category == category:
                    # Additional difficulty filter if specified
                    if difficulty_level:
                        skill_difficulty = self._get_skill_difficulty(skill_info['skills'])
                        if skill_difficulty != difficulty_level:
                            continue
                    
                    filtered_skills.append({
                        'skill': skill_info['skills'],
                        'avg_level': round(skill_info['skill_level'], 1),
                        'avg_rating': round(skill_info['rating'], 2),
                        'description': skill_info['description'],
                        'difficulty': self._get_skill_difficulty(skill_info['skills']),
                        'category': skill_category,
                        'recommendation_type': 'category_based'
                    })
            
            # Sort by rating and return top n
            filtered_skills.sort(key=lambda x: x['avg_rating'], reverse=True)
            return filtered_skills[:n_recommendations]
            
        except Exception as e:
            logger.error(f"Error getting skills by category: {e}")
            return []
    
    def find_skills_by_keywords(self, keywords: List[str], n_recommendations: int = 5,
                               difficulty_level: Optional[str] = None) -> List[Dict]:
        """Search skills by keywords with optional difficulty filtering."""
        if self.skill_vectors is None or self.skill_descriptions.empty:
            return []
        
        try:
            # Create keyword vector
            keyword_text = ' '.join(keywords)
            keyword_vector = self.tfidf_vectorizer.transform([keyword_text])
            
            # Calculate similarities with all skills
            similarities = cosine_similarity(keyword_vector, self.skill_vectors).flatten()
            
            # Filter by difficulty if specified
            if difficulty_level:
                difficulty_levels = self._get_difficulty_levels()
                filtered_indices = [
                    i for i in range(len(self.skill_descriptions))
                    if self._get_skill_difficulty(self.skill_descriptions.iloc[i]['skills']) == difficulty_level
                ]
            else:
                filtered_indices = list(range(len(self.skill_descriptions)))
            
            # Get top matching skills
            keyword_scores = [(i, similarities[i]) for i in filtered_indices]
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            recommendations = []
            for idx, score in keyword_scores[:n_recommendations]:
                if score > 0:  # Only include skills with some similarity
                    skill_info = self.skill_descriptions.iloc[idx]
                    recommendations.append({
                        'skill': skill_info['skills'],
                        'keyword_match_score': float(score),
                        'avg_level': round(skill_info['skill_level'], 1),
                        'avg_rating': round(skill_info['rating'], 2),
                        'description': skill_info['description'],
                        'difficulty': self._get_skill_difficulty(skill_info['skills']),
                        'category': self._get_skill_category(skill_info['skills']),
                        'recommendation_type': 'keyword_search'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error searching skills by keywords: {e}")
            return []
    
    def _get_skill_difficulty(self, skill_name: str) -> str:
        """Determine skill difficulty level based on skill name and description."""
        skill_lower = skill_name.lower()
        
        # Beginner skills
        beginner_keywords = ['basic', 'fundamental', 'introduction', 'beginner', 'git', 'sql', 'html', 'css']
        if any(keyword in skill_lower for keyword in beginner_keywords):
            return 'Beginner'
        
        # Intermediate skills
        intermediate_keywords = ['python', 'javascript', 'react', 'node', 'data analysis', 'design']
        if any(keyword in skill_lower for keyword in intermediate_keywords):
            return 'Intermediate'
        
        # Advanced skills
        advanced_keywords = ['machine learning', 'deep learning', 'ai', 'kubernetes', 'aws', 'cloud']
        if any(keyword in skill_lower for keyword in advanced_keywords):
            return 'Advanced'
        
        # Expert skills
        expert_keywords = ['quantum', 'research', 'architecture', 'advanced']
        if any(keyword in skill_lower for keyword in expert_keywords):
            return 'Expert'
        
        return 'Intermediate'  # Default
    
    def _get_skill_category(self, skill_name: str) -> str:
        """Determine skill category based on skill name."""
        skill_lower = skill_name.lower()
        
        categories = {
            'Programming': ['python', 'javascript', 'react', 'node', 'programming', 'coding'],
            'Design': ['design', 'ux', 'ui', 'figma', 'adobe'],
            'Business': ['marketing', 'product', 'management', 'leadership'],
            'Data': ['data', 'analysis', 'machine learning', 'ai', 'sql'],
            'Cloud': ['aws', 'azure', 'cloud', 'devops', 'docker'],
            'DevOps': ['devops', 'docker', 'kubernetes', 'linux', 'automation']
        }
        
        for category, keywords in categories.items():
            if any(keyword in skill_lower for keyword in keywords):
                return category
        
        return 'Other'
    
    def _skill_matches_category(self, skill_name: str, category: str) -> bool:
        """Check if skill matches a specific category."""
        return self._get_skill_category(skill_name) == category
    
    def _get_difficulty_levels(self) -> List[str]:
        """Get available difficulty levels."""
        return ['Beginner', 'Intermediate', 'Advanced', 'Expert']
    
    def get_stats(self) -> Dict:
        """Get statistics about the content engine."""
        if self.skill_descriptions is None or self.skill_descriptions.empty:
            return {}
        
        total_skills = len(self.skill_descriptions)
        avg_rating = self.skill_descriptions['rating'].mean()
        avg_level = self.skill_descriptions['skill_level'].mean()
        
        # Count skills by difficulty
        difficulty_counts = {}
        for _, skill_info in self.skill_descriptions.iterrows():
            difficulty = self._get_skill_difficulty(skill_info['skills'])
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        return {
            'total_skills': total_skills,
            'avg_rating': round(avg_rating, 2),
            'avg_level': round(avg_level, 2),
            'difficulty_distribution': difficulty_counts,
            'engine_type': 'content_based'
        } 