const express = require('express');
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

const router = express.Router();

// Get data for external recommendation engine in CSV format
router.get('/data', authenticateToken, async (req, res) => {
    try {
        // Get all users with their skills (format like users.csv)
        const usersQuery = `
      SELECT 
        u.id as user_id,
        s.name as skills,
        us.skill_level,
        us.description,
        COALESCE(f.avg_rating, 0) as rating,
        COALESCE(f.feedback_text, '') as feedback,
        'available' as status,
        wanted_skills.skill_names as skill_user_is_seeking_for
      FROM users u
      LEFT JOIN user_skills us ON u.id = us.user_id
      LEFT JOIN skills s ON us.skill_id = s.id
      LEFT JOIN (
        SELECT 
          user_id,
          STRING_AGG(s.name, ', ') as skill_names
        FROM user_skills us2
        JOIN skills s ON us2.skill_id = s.id
        WHERE us2.role = 'wanted'
        GROUP BY user_id
      ) wanted_skills ON u.id = wanted_skills.user_id
      LEFT JOIN (
        SELECT 
          us3.user_id,
          AVG(f2.rating) as avg_rating,
          STRING_AGG(f2.comment, '; ') as feedback_text
        FROM user_skills us3
        LEFT JOIN swaps sw ON (sw.skill_offered_us = us3.id OR sw.skill_requested_us = us3.id)
        LEFT JOIN feedback f2 ON sw.id = f2.swap_id
        WHERE us3.role = 'offered'
        GROUP BY us3.user_id
      ) f ON u.id = f.user_id
      WHERE u.is_public = true AND us.role = 'offered'
      ORDER BY u.id, s.name
    `;

        const usersResult = await db.query(usersQuery);

        // Get all swaps (format like swaps.csv)
        const swapsQuery = `
      SELECT 
        s.from_user_id as user_id_of_learner,
        s.to_user_id as user_id_of_teacher,
        s.created_at as starting_date_of_learning_or_teaching,
        s.ended_at as ending_date_of_learning_or_teaching
      FROM swaps s
      WHERE s.status IN ('accepted', 'pending')
      ORDER BY s.created_at
    `;

        const swapsResult = await db.query(swapsQuery);

        // Transform data into the required format
        const transformedData = {
            users: usersResult.rows.map(row => ({
                user_id: row.user_id,
                skills: row.skills,
                skill_level: row.skill_level || 'Beginner',
                description: row.description,
                rating: parseFloat(row.rating) || 0,
                feedback: row.feedback,
                status: row.status,
                skill_user_is_seeking_for: row.skill_user_is_seeking_for || ''
            })),
            swaps: swapsResult.rows.map(row => ({
                user_id_of_learner: row.user_id_of_learner,
                user_id_of_teacher: row.user_id_of_teacher,
                starting_date_of_learning_or_teaching: row.starting_date_of_learning_or_teaching,
                ending_date_of_learning_or_teaching: row.ending_date_of_learning_or_teaching
            }))
        };

        res.json({
            success: true,
            data: transformedData,
            metadata: {
                total_users: transformedData.users.length,
                total_swaps: transformedData.swaps.length,
                generated_at: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Get recommendation data error:', error);
        res.status(500).json({
            success: false,
            error: 'Internal server error'
        });
    }
});

// Get data for a specific user (for personalized recommendations)
router.get('/user/:userId', authenticateToken, async (req, res) => {
    try {
        const { userId } = req.params;

        // Get user's skills and preferences
        const userSkillsQuery = `
      SELECT 
        u.id as user_id,
        u.name,
        u.bio,
        u.availability,
        s.name as skill_name,
        s.category as skill_category,
        us.role,
        us.skill_level,
        us.description
      FROM users u
      LEFT JOIN user_skills us ON u.id = us.user_id
      LEFT JOIN skills s ON us.skill_id = s.id
      WHERE u.id = $1 AND u.is_public = true
    `;

        const userSkillsResult = await db.query(userSkillsQuery, [userId]);

        if (userSkillsResult.rows.length === 0) {
            return res.status(404).json({
                success: false,
                error: 'User not found'
            });
        }

        // Get user's swap history
        const userSwapsQuery = `
      SELECT 
        s.from_user_id,
        s.to_user_id,
        s.skill_offered_us,
        s.skill_requested_us,
        s.status,
        s.created_at,
        s.ended_at
      FROM swaps s
      WHERE s.from_user_id = $1 OR s.to_user_id = $1
      ORDER BY s.created_at DESC
    `;

        const userSwapsResult = await db.query(userSwapsQuery, [userId]);

        // Transform user data
        const userData = {
            user_id: userSkillsResult.rows[0].user_id,
            name: userSkillsResult.rows[0].name,
            bio: userSkillsResult.rows[0].bio,
            availability: userSkillsResult.rows[0].availability,
            skills_offered: [],
            skills_wanted: [],
            swap_history: userSwapsResult.rows
        };

        userSkillsResult.rows.forEach(row => {
            if (row.skill_name) {
                const skillData = {
                    skill_name: row.skill_name,
                    skill_category: row.skill_category,
                    skill_level: row.skill_level || 'Beginner',
                    description: row.description
                };

                if (row.role === 'offered') {
                    userData.skills_offered.push(skillData);
                } else if (row.role === 'wanted') {
                    userData.skills_wanted.push(skillData);
                }
            }
        });

        res.json({
            success: true,
            data: userData,
            metadata: {
                generated_at: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Get user recommendation data error:', error);
        res.status(500).json({
            success: false,
            error: 'Internal server error'
        });
    }
});

// Get potential matches for a user (for recommendation engine)
router.get('/matches/:userId', authenticateToken, async (req, res) => {
    try {
        const { userId } = req.params;

        // Get user's skills and what they're seeking
        const userQuery = `
      SELECT s.name as skill_name, us.role
      FROM user_skills us
      JOIN skills s ON us.skill_id = s.id
      WHERE us.user_id = $1
    `;

        const userResult = await db.query(userQuery, [userId]);

        if (userResult.rows.length === 0) {
            return res.status(404).json({
                success: false,
                error: 'User not found or has no skills'
            });
        }

        const userOfferedSkills = userResult.rows
            .filter(row => row.role === 'offered')
            .map(row => row.skill_name);

        const userWantedSkills = userResult.rows
            .filter(row => row.role === 'wanted')
            .map(row => row.skill_name);

        // Find potential matches
        const matchesQuery = `
      SELECT DISTINCT
        u.id as user_id,
        u.name,
        u.bio,
        u.availability,
        s.name as skill_name,
        s.category as skill_category,
        us.role,
        us.skill_level,
        us.description
      FROM users u
      JOIN user_skills us ON u.id = us.user_id
      JOIN skills s ON us.skill_id = s.id
      WHERE u.id != $1 
        AND u.is_public = true
        AND (
          (us.role = 'offered' AND s.name = ANY($2)) OR 
          (us.role = 'wanted' AND s.name = ANY($3))
        )
      ORDER BY u.id, s.name
    `;

        const matchesResult = await db.query(matchesQuery, [userId, userWantedSkills, userOfferedSkills]);

        // Transform matches data
        const matchesMap = new Map();

        matchesResult.rows.forEach(row => {
            if (!matchesMap.has(row.user_id)) {
                matchesMap.set(row.user_id, {
                    user_id: row.user_id,
                    name: row.name,
                    bio: row.bio,
                    availability: row.availability,
                    can_teach: [],
                    wants_to_learn: []
                });
            }

            const match = matchesMap.get(row.user_id);

            if (row.role === 'offered' && userWantedSkills.includes(row.skill_name)) {
                match.can_teach.push({
                    skill_name: row.skill_name,
                    skill_category: row.skill_category,
                    skill_level: row.skill_level || 'Beginner',
                    description: row.description
                });
            }

            if (row.role === 'wanted' && userOfferedSkills.includes(row.skill_name)) {
                match.wants_to_learn.push({
                    skill_name: row.skill_name,
                    skill_category: row.skill_category,
                    skill_level: row.skill_level || 'Beginner',
                    description: row.description
                });
            }
        });

        const matches = Array.from(matchesMap.values());

        res.json({
            success: true,
            data: {
                user_id: userId,
                user_offered_skills: userOfferedSkills,
                user_wanted_skills: userWantedSkills,
                potential_matches: matches
            },
            metadata: {
                total_matches: matches.length,
                generated_at: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Get matches error:', error);
        res.status(500).json({
            success: false,
            error: 'Internal server error'
        });
    }
});

// Get homepage user data (for displaying user cards)
router.get('/homepage', async (req, res) => {
    try {
        const { page = 1, limit = 6, search = '' } = req.query;
        const offset = (page - 1) * limit;

        // Build the base query
        let query = `
      SELECT DISTINCT
        u.id,
        u.name,
        u.bio,
        u.photo_url,
        u.availability,
        COALESCE(f.avg_rating, 0) as rating,
        COALESCE(f.total_feedback, 0) as total_feedback,
        COALESCE(offered_skills.skill_list, '') AS offers,
        COALESCE(wanted_skills.skill_list, '')  AS seeks
      FROM users u
      LEFT JOIN (
        SELECT 
          us.user_id,
          STRING_AGG(s.name, ', ') as skill_list
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.role = 'offered'
        GROUP BY us.user_id
      ) offered_skills ON u.id = offered_skills.user_id
      LEFT JOIN (
        SELECT 
          us.user_id,
          STRING_AGG(s.name, ', ') as skill_list
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.role = 'wanted'
        GROUP BY us.user_id
      ) wanted_skills ON u.id = wanted_skills.user_id
      LEFT JOIN (
        SELECT 
          us3.user_id,
          AVG(f2.rating) as avg_rating,
          COUNT(f2.id) as total_feedback
        FROM user_skills us3
        LEFT JOIN swaps sw ON (sw.skill_offered_us = us3.id OR sw.skill_requested_us = us3.id)
        LEFT JOIN feedback f2 ON sw.id = f2.swap_id
        WHERE us3.role = 'offered'
        GROUP BY us3.user_id
      ) f ON u.id = f.user_id
      WHERE u.is_public = true
    `;

        let values = [];
        let valueIndex = 1;

        // Add search filter if provided
        if (search) {
            query += ` AND (
        u.name ILIKE $${valueIndex} OR 
        u.bio ILIKE $${valueIndex} OR
        offered_skills.skill_list ILIKE $${valueIndex} OR
        wanted_skills.skill_list ILIKE $${valueIndex}
      )`;
            values.push(`%${search}%`);
            valueIndex++;
        }

        // Add pagination
        query += ` ORDER BY u.name LIMIT $${valueIndex} OFFSET $${valueIndex + 1}`;
        values.push(parseInt(limit), offset);

        const result = await db.query(query, values);

        // Get total count for pagination
        let countQuery = `
      SELECT COUNT(DISTINCT u.id) as total
      FROM users u
      LEFT JOIN (
        SELECT 
          us.user_id,
          STRING_AGG(s.name, ', ') as skill_list
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.role = 'offered'
        GROUP BY us.user_id
      ) offered_skills ON u.id = offered_skills.user_id
      LEFT JOIN (
        SELECT 
          us.user_id,
          STRING_AGG(s.name, ', ') as skill_list
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.role = 'wanted'
        GROUP BY us.user_id
      ) wanted_skills ON u.id = wanted_skills.user_id
      WHERE u.is_public = true
    `;

        let countValues = [];
        if (search) {
            countQuery += ` AND (
        u.name ILIKE $1 OR 
        u.bio ILIKE $1 OR
        offered_skills.skill_list ILIKE $1 OR
        wanted_skills.skill_list ILIKE $1
      )`;
            countValues.push(`%${search}%`);
        }

        const countResult = await db.query(countQuery, countValues);
        const totalUsers = parseInt(countResult.rows[0].total);

        // Transform data for frontend
        const users = result.rows.map(row => ({
            id: row.id,
            name: row.name,
            initial: row.name.charAt(0).toUpperCase(),
            rating: parseFloat(row.rating) || 0,
            total_feedback: parseInt(row.total_feedback) || 0,
            offers: row.offers ? row.offers : '',
            seeks: row.seeks ? row.seeks : '',
            bio: row.bio,
            photo_url: row.photo_url,
            availability: row.availability
        }));

        res.json({
            success: true,
            data: {
                users,
                pagination: {
                    current_page: parseInt(page),
                    total_pages: Math.ceil(totalUsers / limit),
                    total_users: totalUsers,
                    users_per_page: parseInt(limit)
                }
            }
        });

    } catch (error) {
        console.error('Get homepage data error:', error);
        res.status(500).json({
            success: false,
            error: 'Internal server error'
        });
    }
});

module.exports = router; 