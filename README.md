# Skill Swap Recommendation Engine (Simplified)

A simplified real-time skill recommendation engine for a "Skill Swap" web application. This system provides personalized skill recommendations based on user skills, ratings, and learning history.

## Features

- **Advanced Recommendation Algorithms**: 
  - Simple skill-based recommendations
  - Content-based filtering with semantic understanding
  - Collaborative filtering for personalized recommendations
- **Rich Data Structure**: Uses `users.csv` and `swaps.csv` with descriptions and ratings
- **Semantic Understanding**: TF-IDF vectorization for skill similarity
- **Learning History**: Tracks user learning progress through skill swaps
- **Automatic Status Tracking**: Updates user availability based on active sessions
- **In-memory Caching**: Fast response times with in-memory caching
- **RESTful API**: Clean FastAPI endpoints for easy integration
- **Optional API Key Authentication**: Secure endpoints with optional authentication

## Data Structure

### users.csv
Contains user skill information with the following columns:
- `user_id`: Unique user identifier
- `skills`: Skill name
- `skill_level`: Skill proficiency level (1-5)
- `description`: User description/bio
- `rating`: User's rating for the skill
- `feedback`: User feedback about the skill
- `status`: User availability status (available/busy)
- `skill_user_is_seeking_for`: Skills the user wants to learn

### swaps.csv
Contains learning history with the following columns:
- `user_id_of_learner`: ID of the user learning the skill
- `user_id_of_teacher`: ID of the user teaching the skill
- `starting_date_of_learning_or_teaching`: Date when learning started
- `ending_date_of_learning_or_teaching`: Date when learning ended (for status tracking)

## Project Structure

```
├── main.py                           # FastAPI application
├── simple_recommendation_engine.py   # Simple recommendation engine
├── faiss_engine.py                  # Content-based filtering engine
├── collab_filter.py                 # Collaborative filtering engine
├── test_simple.py                   # Test suite
├── requirements.txt                 # Dependencies
├── data/                           # Sample data
│   ├── users.csv                   # User skills and profiles
│   └── swaps.csv                   # Learning history
└── README.md                       # This file
```

## Installation
   ```bash
   git clone <repository-url>
   cd skill-swap-recommender
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint with system info
- `GET /health` - Health check
- `GET /recommend/{user_id}` - Get simple recommendations for a user
- `POST /recommend` - Trigger new recommendations
- `POST /update-profile` - Update user profile
- `GET /stats` - Get system statistics
- `GET /user/status/{user_id}` - Get user status and active sessions
- `GET /users/active-sessions` - Get all users with active learning sessions

### Advanced Recommendation Endpoints

- `GET /recommend/content/{user_id}` - Get content-based recommendations
- `GET /recommend/collaborative/{user_id}` - Get collaborative filtering recommendations
- `GET /similar-skills/{skill_name}` - Find skills similar to a given skill
- `GET /skills/difficulty/{difficulty_level}` - Get skills by difficulty level
- `GET /skills/category/{category}` - Get skills by category
- `GET /skills/search` - Search skills by keywords
- `GET /similar-users/{user_id}` - Find users similar to a given user
- `GET /user/learning-patterns/{user_id}` - Get user's learning patterns
- `GET /skill/popularity/{skill_name}` - Get skill popularity metrics

### Cache Management

- `DELETE /cache/{user_id}` - Clear user cache
- `POST /cache/flush` - Flush all cache
- `GET /cache/keys` - List cache keys

## Usage Examples

### Get Recommendations
```bash
curl -X GET "http://localhost:8000/recommend/1"
```

### Trigger Recommendations
```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "force_refresh": true}'
```

### Update User Profile
```bash
curl -X POST "http://localhost:8000/update-profile" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "bio": "Updated bio", "skills": ["Python", "JavaScript"]}'
```

### Get System Stats
```bash
curl -X GET "http://localhost:8000/stats"
```

### Get User Status
```bash
curl -X GET "http://localhost:8000/user/status/1"
```

### Get Active Sessions
```bash
curl -X GET "http://localhost:8000/users/active-sessions"
```

### Get Content-Based Recommendations
```bash
curl -X GET "http://localhost:8000/recommend/content/1"
```

### Get Collaborative Filtering Recommendations
```bash
curl -X GET "http://localhost:8000/recommend/collaborative/1"
```

### Find Similar Skills
```bash
curl -X GET "http://localhost:8000/similar-skills/Python%20Programming"
```

### Get Skills by Difficulty
```bash
curl -X GET "http://localhost:8000/skills/difficulty/Intermediate"
```

### Search Skills by Keywords
```bash
curl -X GET "http://localhost:8000/skills/search?keywords=python,web,development"
```

### Get User Learning Patterns
```bash
curl -X GET "http://localhost:8000/user/learning-patterns/1"
```

## Configuration

### Environment Variables

- `API_KEY_ENABLED`: Enable API key authentication (default: false)
- `API_KEY`: Your secret API key (default: "your-secret-api-key-here")

### API Key Authentication

To enable API key authentication:

1. Set environment variables:
   ```bash
   export API_KEY_ENABLED=true
   export API_KEY=your-secret-key
   ```

2. Include the API key in requests:
   ```bash
   curl -H "Authorization: Bearer your-secret-key" \
        -X GET "http://localhost:8000/recommend/1"
   ```

## Data Format

### Sample users.csv
```csv
user_id,skills,skill_level,description,rating,feedback,status,skill_user_is_seeking_for
1,Python Programming,4,"Software developer passionate about Python",4.5,"Excellent course","available","Machine Learning"
1,Data Analysis,3,"Software developer passionate about Python",4.0,"Good content","available","Machine Learning"
```

### Sample swaps.csv
```csv
user_id_of_learner,user_id_of_teacher,starting_date_of_learning_or_teaching,ending_date_of_learning_or_teaching
1,2,2024-01-15,2024-03-15
1,8,2024-02-10,2024-04-10
2,15,2024-01-20,2024-03-20
```

## Recommendation Algorithms

The system uses multiple sophisticated recommendation approaches:

### 1. **Simple Skill-Based Recommendations**
- Skills to Learn: Based on what the user is seeking to learn
- Skills to Offer: Based on user's high-level skills (level 4-5) with good ratings
- Popularity Scoring: Considers skill popularity and average ratings

### 2. **Content-Based Filtering**
- **TF-IDF Vectorization**: Converts skill descriptions into numerical vectors
- **Semantic Understanding**: Uses skill descriptions, feedback, and seeking preferences
- **Similarity Matching**: Finds skills similar to user's current skills
- **Difficulty Filtering**: Filters by Beginner, Intermediate, Advanced, Expert levels
- **Category Filtering**: Groups skills by Programming, Design, Business, Data, Cloud, DevOps

### 3. **Collaborative Filtering**
- **User-Skill Matrix**: Creates interaction matrix from skill levels and ratings
- **Cosine Similarity**: Finds users with similar skill profiles
- **Personalized Recommendations**: Recommends skills that similar users have
- **Learning Pattern Analysis**: Analyzes user's learning history and preferences
- **Explanation Generation**: Provides reasoning for recommendations

### 4. **Advanced Features**
- **Status Tracking**: Automatically updates user status based on active learning sessions
- **Learning History**: Tracks user's learning progress through swaps
- **Popularity Metrics**: Calculates skill popularity and difficulty distributions

## Performance

- **Fast Response**: In-memory caching provides sub-second response times
- **Scalable**: Simple architecture can handle thousands of users
- **Lightweight**: Minimal dependencies, easy to deploy

## Development

### Running Tests
```bash
# Run basic tests
python -m pytest test_simple.py -v

# Run advanced tests (content-based and collaborative filtering)
python -m pytest test_advanced.py -v

# Run all tests
python -m pytest test_*.py -v
```

### Adding New Features
1. Update the `SimpleRecommendationEngine` class
2. Add new endpoints to `main.py`
3. Update data files as needed
4. Add tests to `test_simple.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request 
