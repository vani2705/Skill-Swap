from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import logging
import json
import os
from datetime import datetime, timedelta

from simple_recommendation_engine import SimpleRecommendationEngine
from faiss_engine import FAISSContentEngine
from collab_filter import CollaborativeFilterEngine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional API Key Authentication
API_KEY_ENABLED = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
API_KEY = os.getenv('API_KEY', 'your-secret-api-key-here')

# Initialize FastAPI app
app = FastAPI(
    title="Skill Swap Recommendation Engine (Simple)",
    description="Simplified real-time skill recommendation engine for Skill Swap platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache only - no Redis
cache = {}
logger.info("Using in-memory cache only - no Redis required")

# Initialize recommendation engines
recommendation_engine = SimpleRecommendationEngine()
content_engine = FAISSContentEngine()
collab_engine = CollaborativeFilterEngine()

# Optional API Key Authentication
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify API key if enabled."""
    if not API_KEY_ENABLED:
        return True  # No authentication required
    
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail="API key required. Add Authorization: Bearer your-api-key header"
        )
    
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Invalid API key"
        )
    
    return True

# Pydantic models
class UserProfile(BaseModel):
    user_id: int
    bio: Optional[str] = ""
    skills: Optional[List[str]] = []

class RecommendationRequest(BaseModel):
    user_id: int
    force_refresh: Optional[bool] = False

class RecommendationResponse(BaseModel):
    user_id: int
    user_swap_count: int
    recommendation_type: str
    skills_to_learn: List[Dict]
    skills_to_offer: List[Dict]
    weights: Dict
    timestamp: str
    cache_hit: bool

# Data loading functions
def load_sample_data():
    """Load sample data for demonstration."""
    try:
        # Load sample CSV files
        users_df = pd.read_csv('data/users.csv')
        swaps_df = pd.read_csv('data/swaps.csv')
        
        # Initialize all recommendation engines
        recommendation_engine.load_data(users_df, swaps_df)
        content_engine.load_data(users_df, swaps_df)
        collab_engine.load_data(users_df, swaps_df)
        
        logger.info("Sample data loaded successfully for all engines")
        return True
    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        return False

def get_cache_key(user_id: int) -> str:
    """Generate cache key for user recommendations."""
    return f"recommendations:{user_id}"

def get_cached_recommendations(user_id: int) -> Optional[Dict]:
    """Get cached recommendations for a user from in-memory cache."""
    cache_key = get_cache_key(user_id)
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"In-memory cache hit for user {user_id}")
    return cached_data

def cache_recommendations(user_id: int, recommendations: Dict, ttl_seconds: int = 3600):
    """Cache recommendations in memory with TTL."""
    cache_key = get_cache_key(user_id)
    recommendations['timestamp'] = datetime.now().isoformat()
    recommendations['cached_at'] = datetime.now().isoformat()
    
    # Store in in-memory cache
    cache[cache_key] = recommendations
    logger.debug(f"Cached recommendations for user {user_id} in memory")

def update_user_profile_background(user_id: int, bio: str, skills: List[str]):
    """Background task to update user profile and refresh recommendations."""
    try:
        logger.info(f"Updating profile for user {user_id}")
        
        # Force refresh recommendations
        recommendations = recommendation_engine.get_recommendations(user_id)
        cache_recommendations(user_id, recommendations)
        
        logger.info(f"Profile updated and recommendations refreshed for user {user_id}")
    except Exception as e:
        logger.error(f"Background update failed for user {user_id}: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting Simple Skill Swap Recommendation Engine...")
    
    # Load sample data
    if not load_sample_data():
        logger.warning("Failed to load sample data. Some endpoints may not work properly.")

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up template engine
templates = Jinja2Templates(directory="templates")

# Route to serve index.html as homepage
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Skill Swap Home"})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_type": "in_memory",
        "cache_size": len(cache)
    }

@app.get("/recommend/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(user_id: int, force_refresh: bool = False, auth: bool = Depends(verify_api_key)):
    """
    Get skill recommendations for a user.
    
    Args:
        user_id: The user ID to get recommendations for
        force_refresh: Force refresh recommendations (bypass cache)
    """
    try:
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_recs = get_cached_recommendations(user_id)
            if cached_recs:
                cached_recs['cache_hit'] = True
                return RecommendationResponse(**cached_recs)
        
        # Generate new recommendations
        recommendations = recommendation_engine.get_recommendations(user_id)
        recommendations['cache_hit'] = False
        
        # Cache the results
        cache_recommendations(user_id, recommendations)
        
        # Save recommendations as JSON file in 'recommendation' folder
        import os, json
        os.makedirs("recommendation", exist_ok=True)
        file_path = os.path.join("recommendation", f"user_{user_id}_recommendation.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        
        return RecommendationResponse(**recommendations)
        
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@app.post("/recommend")
async def trigger_recommendations(request: RecommendationRequest, background_tasks: BackgroundTasks, auth: bool = Depends(verify_api_key)):
    """
    Trigger new recommendations based on updated user profile.
    This endpoint is designed to be called by webhooks (e.g., n8n).
    """
    try:
        user_id = request.user_id
        
        # Force refresh recommendations
        recommendations = recommendation_engine.get_recommendations(user_id)
        recommendations['cache_hit'] = False
        
        # Cache the results
        cache_recommendations(user_id, recommendations)
        
        # Add background task to update models if needed
        background_tasks.add_task(update_user_profile_background, user_id, "", [])
        
        return {
            "message": "Recommendations updated successfully",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "recommendations_count": {
                "skills_to_learn": len(recommendations.get('skills_to_learn', [])),
                "skills_to_offer": len(recommendations.get('skills_to_offer', []))
            }
        }
        
    except Exception as e:
        logger.error(f"Error triggering recommendations for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger recommendations: {str(e)}")

@app.post("/update-profile")
async def update_user_profile(user_profile: UserProfile, background_tasks: BackgroundTasks, auth: bool = Depends(verify_api_key)):
    """
    Update user profile and refresh recommendations.
    """
    try:
        user_id = user_profile.user_id
        
        # In a real application, this would update the database
        logger.info(f"Updating profile for user {user_id}")
        
        # Add background task to refresh recommendations
        background_tasks.add_task(
            update_user_profile_background, 
            user_id, 
            user_profile.bio, 
            user_profile.skills
        )
        
        return {
            "message": "Profile update initiated",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating profile for user {user_profile.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

@app.delete("/cache/{user_id}")
async def clear_user_cache(user_id: int, auth: bool = Depends(verify_api_key)):
    """Clear cached recommendations for a user from memory."""
    try:
        cache_key = get_cache_key(user_id)
        
        # Clear in-memory cache
        if cache_key in cache:
            del cache[cache_key]
            logger.info(f"Cleared in-memory cache for user {user_id}")
        
        return {
            "message": "Cache cleared successfully",
            "user_id": user_id,
            "cleared_sources": ["memory"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        # Get stats from all engines
        simple_stats = recommendation_engine.get_stats()
        content_stats = content_engine.get_stats()
        collab_stats = collab_engine.get_stats()
        
        # Get cache stats
        cache_stats = {
            "size": len(cache),
            "type": "in_memory"
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": cache_stats,
            "engines": {
                "simple_engine": simple_stats,
                "content_engine": content_stats,
                "collaborative_engine": collab_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/recommend/content/{user_id}")
async def get_content_recommendations(user_id: int, n_recommendations: int = 5, auth: bool = Depends(verify_api_key)):
    """Get content-based recommendations for a user."""
    try:
        # Get user's skills from the simple engine
        user_skills = []
        if recommendation_engine.users_df is not None:
            user_data = recommendation_engine.users_df[recommendation_engine.users_df['user_id'] == user_id]
            user_skills = user_data['skills'].tolist()
        
        recommendations = content_engine.get_user_skill_recommendations(user_skills, n_recommendations)
        return {
            "user_id": user_id,
            "recommendation_type": "content_based",
            "user_skills": user_skills,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting content recommendations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get content recommendations: {str(e)}")

@app.get("/recommend/collaborative/{user_id}")
async def get_collaborative_recommendations(user_id: int, n_recommendations: int = 5, auth: bool = Depends(verify_api_key)):
    """Get collaborative filtering recommendations for a user."""
    try:
        recommendations = collab_engine.get_recommendations(user_id, n_recommendations)
        return {
            "user_id": user_id,
            "recommendation_type": "collaborative",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting collaborative recommendations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collaborative recommendations: {str(e)}")

@app.get("/similar-skills/{skill_name}")
async def get_similar_skills(skill_name: str, n_recommendations: int = 5, 
                           difficulty_filter: Optional[str] = None, auth: bool = Depends(verify_api_key)):
    """Get skills similar to a given skill using content-based filtering."""
    try:
        recommendations = content_engine.find_similar_skills(skill_name, n_recommendations, difficulty_filter)
        return {
            "skill_name": skill_name,
            "difficulty_filter": difficulty_filter,
            "recommendation_type": "similar_skills",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting similar skills for skill {skill_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar skills: {str(e)}")

@app.get("/skills/difficulty/{difficulty_level}")
async def get_skills_by_difficulty(difficulty_level: str, category: Optional[str] = None,
                                 n_recommendations: int = 10, auth: bool = Depends(verify_api_key)):
    """Get skills filtered by difficulty level and optionally by category."""
    try:
        recommendations = content_engine.get_skills_by_difficulty(difficulty_level, category, n_recommendations)
        return {
            "difficulty_level": difficulty_level,
            "category_filter": category,
            "recommendation_type": "difficulty_based",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting skills by difficulty {difficulty_level}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get skills by difficulty: {str(e)}")

@app.get("/skills/category/{category}")
async def get_skills_by_category(category: str, difficulty_level: Optional[str] = None,
                               n_recommendations: int = 10, auth: bool = Depends(verify_api_key)):
    """Get skills filtered by category and optionally by difficulty level."""
    try:
        recommendations = content_engine.get_skills_by_category(category, difficulty_level, n_recommendations)
        return {
            "category": category,
            "difficulty_filter": difficulty_level,
            "recommendation_type": "category_based",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting skills by category {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get skills by category: {str(e)}")

@app.get("/skills/search")
async def search_skills_by_keywords(keywords: str, difficulty_level: Optional[str] = None,
                                  n_recommendations: int = 5, auth: bool = Depends(verify_api_key)):
    """Search skills by keywords with optional difficulty filtering."""
    try:
        keyword_list = [kw.strip() for kw in keywords.split(',')]
        recommendations = content_engine.find_skills_by_keywords(keyword_list, n_recommendations, difficulty_level)
        return {
            "keywords": keyword_list,
            "difficulty_filter": difficulty_level,
            "recommendation_type": "keyword_search",
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error searching skills with keywords {keywords}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search skills: {str(e)}")

@app.get("/similar-users/{user_id}")
async def get_similar_users(user_id: int, n_similar: int = 10, auth: bool = Depends(verify_api_key)):
    """Get users similar to a given user using collaborative filtering."""
    try:
        similar_users = collab_engine._get_similar_users(user_id, n_similar)
        return {
            "user_id": user_id,
            "recommendation_type": "similar_users",
            "similar_users": [{"user_id": uid, "similarity": sim} for uid, sim in similar_users],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting similar users for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar users: {str(e)}")

@app.get("/user/learning-patterns/{user_id}")
async def get_user_learning_patterns(user_id: int, auth: bool = Depends(verify_api_key)):
    """Get user's learning patterns and preferences."""
    try:
        patterns = collab_engine.get_user_learning_patterns(user_id)
        return {
            "user_id": user_id,
            "learning_patterns": patterns,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting learning patterns for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get learning patterns: {str(e)}")

@app.get("/skill/popularity/{skill_name}")
async def get_skill_popularity(skill_name: str, auth: bool = Depends(verify_api_key)):
    """Get popularity metrics for a specific skill."""
    try:
        popularity = collab_engine.get_skill_popularity(skill_name)
        return {
            "skill_name": skill_name,
            "popularity_metrics": popularity,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting skill popularity for {skill_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get skill popularity: {str(e)}")

@app.get("/user/status/{user_id}")
async def get_user_status(user_id: int, auth: bool = Depends(verify_api_key)):
    """Get current user status and active learning sessions."""
    try:
        status = recommendation_engine.get_user_status(user_id)
        learning_history = recommendation_engine._get_learning_history(user_id)
        active_sessions = [h for h in learning_history if h.get('is_active', False)]
        
        return {
            "user_id": user_id,
            "status": status,
            "active_sessions": active_sessions,
            "total_sessions": len(learning_history),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user status for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user status: {str(e)}")

@app.get("/users/active-sessions")
async def get_active_sessions(auth: bool = Depends(verify_api_key)):
    """Get all users with active learning sessions."""
    try:
        if recommendation_engine.swaps_df is None:
            return {"active_users": []}
        
        active_users = []
        current_date = datetime.now().date()
        
        for _, swap in recommendation_engine.swaps_df.iterrows():
            try:
                start_date = datetime.strptime(swap['starting_date_of_learning_or_teaching'], '%Y-%m-%d').date()
                end_date = datetime.strptime(swap['ending_date_of_learning_or_teaching'], '%Y-%m-%d').date()
                
                if start_date <= current_date <= end_date:
                    # Check if user already in list
                    learner_exists = any(u['user_id'] == swap['user_id_of_learner'] for u in active_users)
                    teacher_exists = any(u['user_id'] == swap['user_id_of_teacher'] for u in active_users)
                    
                    if not learner_exists:
                        active_users.append({
                            "user_id": swap['user_id_of_learner'],
                            "role": "learner",
                            "partner_id": swap['user_id_of_teacher'],
                            "start_date": swap['starting_date_of_learning_or_teaching'],
                            "end_date": swap['ending_date_of_learning_or_teaching']
                        })
                    
                    if not teacher_exists:
                        active_users.append({
                            "user_id": swap['user_id_of_teacher'],
                            "role": "teacher",
                            "partner_id": swap['user_id_of_learner'],
                            "start_date": swap['starting_date_of_learning_or_teaching'],
                            "end_date": swap['ending_date_of_learning_or_teaching']
                        })
            except:
                continue
        
        return {
            "active_users": active_users,
            "count": len(active_users),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active sessions: {str(e)}")

@app.post("/cache/flush")
async def flush_cache(auth: bool = Depends(verify_api_key)):
    """Flush all cached data from memory."""
    try:
        cache_size = len(cache)
        cache.clear()
        
        logger.info(f"Flushed {cache_size} cached items from memory")
        
        return {
            "message": "Cache flushed successfully",
            "cleared_items": cache_size,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error flushing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to flush cache: {str(e)}")

@app.get("/cache/keys")
async def get_cache_keys(auth: bool = Depends(verify_api_key)):
    """Get list of all cache keys in memory."""
    try:
        cache_keys = list(cache.keys())
        
        return {
            "cache_keys": cache_keys,
            "total_keys": len(cache_keys),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache keys: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache keys: {str(e)}")

@app.get("/recommend/tfidf/{user_id}")
async def recommend_tfidf(user_id: int, n_recommendations: int = 5):
    """
    Recommend users based on all features using TF-IDF and cosine similarity.
    Also saves the recommendation result as a JSON file in the 'recommendation' folder.
    """
    try:
        users_df = pd.read_csv("data/users.csv")
        users_df['combined_features'] = users_df.apply(lambda row: ' '.join([
            str(row['skills']),
            str(row['skill_level']),
            str(row['description']),
            str(row['rating']),
            str(row['feedback']),
            str(row['status']),
            str(row['skill_user_is_seeking_for'])
        ]), axis=1)
        grouped = users_df.groupby('user_id')['combined_features'].apply(lambda x: ' '.join(x)).reset_index()
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(grouped['combined_features'])
        if user_id not in grouped['user_id'].values:
            raise HTTPException(status_code=404, detail="User ID not found")
        user_idx = grouped[grouped['user_id'] == user_id].index[0]
        user_vector = tfidf_matrix[user_idx]
        similarities = cosine_similarity(user_vector, tfidf_matrix).flatten()
        similar_indices = similarities.argsort()[::-1]
        recommendations = []
        for idx in similar_indices:
            rec_user_id = int(grouped.iloc[idx]['user_id'])
            if rec_user_id != user_id:
                recommendations.append({
                    "user_id": rec_user_id,
                    "similarity": float(similarities[idx])
                })
            if len(recommendations) >= n_recommendations:
                break
        seeking_skills = users_df[users_df['user_id'] == user_id]['skill_user_is_seeking_for'].unique().tolist()
        result = {
            "requested_user_id": user_id,
            "seeking_skills": seeking_skills,
            "recommended_users": recommendations
        }
        # Save to recommendation folder as JSON
        os.makedirs("recommendation", exist_ok=True)
        file_path = os.path.join("recommendation", f"user_{user_id}_recommendation.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result
    except Exception as e:
        logger.error(f"Error in TF-IDF recommendation for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get TF-IDF recommendations: {str(e)}")

@app.get("/recommend/star/{user_id}")
async def recommend_star(user_id: int):
    """
    Find all users who are a perfect mutual (star) match:
    - The given user has a skill the other is seeking
    - The other user has a skill the given user is seeking
    """
    try:
        users_df = pd.read_csv("data/users.csv")
        # Get all skills and seeking skills for the user
        user_skills = set(users_df[users_df['user_id'] == user_id]['skills'])
        user_seeking = set(users_df[users_df['user_id'] == user_id]['skill_user_is_seeking_for'])
        if not user_skills or not user_seeking:
            return {"user_id": user_id, "star_matches": []}
        star_matches = []
        # For each other user
        for other_id in users_df['user_id'].unique():
            if other_id == user_id:
                continue
            other_skills = set(users_df[users_df['user_id'] == other_id]['skills'])
            other_seeking = set(users_df[users_df['user_id'] == other_id]['skill_user_is_seeking_for'])
            # Check for mutual match
            # User has a skill the other is seeking, and vice versa
            if user_skills & other_seeking and other_skills & user_seeking:
                star_matches.append({
                    "matched_user_id": int(other_id),
                    "user_skills": list(user_skills),
                    "user_seeking": list(user_seeking),
                    "matched_user_skills": list(other_skills),
                    "matched_user_seeking": list(other_seeking)
                })
        return {"user_id": user_id, "star_matches": star_matches}
    except Exception as e:
        logger.error(f"Error in star recommender for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get star recommendations: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 