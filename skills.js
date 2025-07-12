const express = require('express');
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');
const { validateSkill, validateUserSkill } = require('../middleware/validation');

const router = express.Router();

// Get all skills
router.get('/', async (req, res) => {
  try {
    const { category } = req.query;
    let query = 'SELECT id, name, category FROM skills ORDER BY category, name';
    let values = [];

    if (category) {
      query = 'SELECT id, name, category FROM skills WHERE category = $1 ORDER BY name';
      values = [category];
    }

    const result = await db.query(query, values);
    res.json({ skills: result.rows });
  } catch (error) {
    console.error('Get skills error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get skills by category
router.get('/categories', async (req, res) => {
  try {
    const result = await db.query(
      'SELECT DISTINCT category FROM skills ORDER BY category'
    );
    res.json({ categories: result.rows.map(row => row.category) });
  } catch (error) {
    console.error('Get categories error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add new skill (admin only - simplified for demo)
router.post('/', authenticateToken, validateSkill, async (req, res) => {
  try {
    const { name, category } = req.body;

    // Check if skill already exists
    const existingSkill = await db.query(
      'SELECT id FROM skills WHERE LOWER(name) = LOWER($1)',
      [name]
    );

    if (existingSkill.rows.length > 0) {
      return res.status(400).json({ error: 'Skill already exists' });
    }

    const result = await db.query(
      'INSERT INTO skills (name, category) VALUES ($1, $2) RETURNING id, name, category',
      [name, category]
    );

    res.status(201).json({
      message: 'Skill added successfully',
      skill: result.rows[0]
    });
  } catch (error) {
    console.error('Add skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user's skills
router.get('/user', authenticateToken, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT us.id, us.role, us.skill_level, us.description, s.id as skill_id, s.name, s.category
       FROM user_skills us
       JOIN skills s ON us.skill_id = s.id
       WHERE us.user_id = $1
       ORDER BY s.category, s.name`,
      [req.user.id]
    );

    res.json({ userSkills: result.rows });
  } catch (error) {
    console.error('Get user skills error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add skill to user
router.post('/user', authenticateToken, validateUserSkill, async (req, res) => {
  try {
    const { skill_id, role, skill_level, description } = req.body;

    // Check if skill exists
    const skillExists = await db.query('SELECT id FROM skills WHERE id = $1', [skill_id]);
    if (skillExists.rows.length === 0) {
      return res.status(404).json({ error: 'Skill not found' });
    }

    // Check if user already has this skill with this role
    const existingUserSkill = await db.query(
      'SELECT id FROM user_skills WHERE user_id = $1 AND skill_id = $2 AND role = $3',
      [req.user.id, skill_id, role]
    );

    if (existingUserSkill.rows.length > 0) {
      return res.status(400).json({ error: 'User already has this skill with this role' });
    }

    const result = await db.query(
      `INSERT INTO user_skills (user_id, skill_id, role, skill_level, description)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, role, skill_level, description`,
      [req.user.id, skill_id, role, skill_level || 'Beginner', description]
    );

    // Get the skill details
    const skillResult = await db.query(
      'SELECT id, name, category FROM skills WHERE id = $1',
      [skill_id]
    );

    res.status(201).json({
      message: 'Skill added to user successfully',
      userSkill: {
        ...result.rows[0],
        skill: skillResult.rows[0]
      }
    });
  } catch (error) {
    console.error('Add user skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user skill
router.put('/user/:id', authenticateToken, validateUserSkill, async (req, res) => {
  try {
    const { id } = req.params;
    const { skill_level, description } = req.body;

    const result = await db.query(
      `UPDATE user_skills 
       SET skill_level = $1, description = $2
       WHERE id = $3 AND user_id = $4
       RETURNING id, role, skill_level, description`,
      [skill_level, description, id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User skill not found' });
    }

    res.json({
      message: 'User skill updated successfully',
      userSkill: result.rows[0]
    });
  } catch (error) {
    console.error('Update user skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Remove skill from user
router.delete('/user/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;

    const result = await db.query(
      'DELETE FROM user_skills WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User skill not found' });
    }

    res.json({ message: 'Skill removed from user successfully' });
  } catch (error) {
    console.error('Remove user skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get users by skill (for finding potential swaps)
router.get('/:skillId/users', async (req, res) => {
  try {
    const { skillId } = req.params;
    const { role } = req.query;

    let query = `
      SELECT u.id, u.name, u.bio, u.location, u.photo_url, u.availability, us.role, us.skill_level, us.description
      FROM users u
      JOIN user_skills us ON u.id = us.user_id
      WHERE us.skill_id = $1 AND u.is_public = true
    `;
    let values = [skillId];

    if (role) {
      query += ' AND us.role = $2';
      values.push(role);
    }

    query += ' ORDER BY u.name';

    const result = await db.query(query, values);

    res.json({ users: result.rows });
  } catch (error) {
    console.error('Get users by skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router; 