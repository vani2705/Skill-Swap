const express = require('express');
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');
const { validateFeedback } = require('../middleware/validation');

const router = express.Router();

// Submit feedback for a completed swap
router.post('/', authenticateToken, validateFeedback, async (req, res) => {
  try {
    const { swap_id, rating, comment } = req.body;

    // Check if swap exists and is completed
    const swapResult = await db.query(
      'SELECT * FROM swaps WHERE id = $1 AND status = $2',
      [swap_id, 'accepted']
    );

    if (swapResult.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found or not completed' });
    }

    const swap = swapResult.rows[0];

    // Check if user is part of this swap
    if (swap.from_user_id !== req.user.id && swap.to_user_id !== req.user.id) {
      return res.status(403).json({ error: 'Not authorized to provide feedback for this swap' });
    }

    // Check if user already provided feedback for this swap
    const existingFeedback = await db.query(
      'SELECT id FROM feedback WHERE swap_id = $1 AND from_user = $2',
      [swap_id, req.user.id]
    );

    if (existingFeedback.rows.length > 0) {
      return res.status(400).json({ error: 'You have already provided feedback for this swap' });
    }

    const result = await db.query(
      `INSERT INTO feedback (swap_id, from_user, rating, comment)
       VALUES ($1, $2, $3, $4)
       RETURNING id, swap_id, from_user, rating, comment, created_at`,
      [swap_id, req.user.id, rating, comment]
    );

    res.status(201).json({
      message: 'Feedback submitted successfully',
      feedback: result.rows[0]
    });
  } catch (error) {
    console.error('Submit feedback error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get feedback for a specific swap
router.get('/swap/:swapId', authenticateToken, async (req, res) => {
  try {
    const { swapId } = req.params;

    // Check if user is part of this swap
    const swapResult = await db.query(
      'SELECT * FROM swaps WHERE id = $1 AND (from_user_id = $2 OR to_user_id = $2)',
      [swapId, req.user.id]
    );

    if (swapResult.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found' });
    }

    const result = await db.query(
      `SELECT f.id, f.rating, f.comment, f.created_at,
              u.name as from_user_name
       FROM feedback f
       JOIN users u ON f.from_user = u.id
       WHERE f.swap_id = $1
       ORDER BY f.created_at DESC`,
      [swapId]
    );

    res.json({ feedback: result.rows });
  } catch (error) {
    console.error('Get swap feedback error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user's feedback history
router.get('/user', authenticateToken, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT f.id, f.rating, f.comment, f.created_at,
              s.id as swap_id,
              other_user.name as other_user_name,
              offered_skill_s.name as offered_skill_name,
              requested_skill_s.name as requested_skill_name
       FROM feedback f
       JOIN swaps s ON f.swap_id = s.id
       JOIN users other_user ON (s.from_user_id = $1 AND s.to_user_id = other_user.id) 
                              OR (s.to_user_id = $1 AND s.from_user_id = other_user.id)
       JOIN user_skills offered_skill ON s.skill_offered_us = offered_skill.id
       JOIN user_skills requested_skill ON s.skill_requested_us = requested_skill.id
       JOIN skills offered_skill_s ON offered_skill.skill_id = offered_skill_s.id
       JOIN skills requested_skill_s ON requested_skill.skill_id = requested_skill_s.id
       WHERE f.from_user = $1
       ORDER BY f.created_at DESC`,
      [req.user.id]
    );

    res.json({ feedback: result.rows });
  } catch (error) {
    console.error('Get user feedback error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get feedback received by a user
router.get('/received', authenticateToken, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT f.id, f.rating, f.comment, f.created_at,
              s.id as swap_id,
              from_user.name as from_user_name,
              offered_skill_s.name as offered_skill_name,
              requested_skill_s.name as requested_skill_name
       FROM feedback f
       JOIN swaps s ON f.swap_id = s.id
       JOIN users from_user ON f.from_user = from_user.id
       JOIN user_skills offered_skill ON s.skill_offered_us = offered_skill.id
       JOIN user_skills requested_skill ON s.skill_requested_us = requested_skill.id
       JOIN skills offered_skill_s ON offered_skill.skill_id = offered_skill_s.id
       JOIN skills requested_skill_s ON requested_skill.skill_id = requested_skill_s.id
       WHERE (s.from_user_id = $1 OR s.to_user_id = $1) AND f.from_user != $1
       ORDER BY f.created_at DESC`,
      [req.user.id]
    );

    res.json({ feedback: result.rows });
  } catch (error) {
    console.error('Get received feedback error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user's average rating
router.get('/user/:userId/rating', async (req, res) => {
  try {
    const { userId } = req.params;

    // Check if user exists and is public
    const userExists = await db.query(
      'SELECT id FROM users WHERE id = $1 AND is_public = true',
      [userId]
    );

    if (userExists.rows.length === 0) {
      return res.status(404).json({ error: 'User not found or profile is private' });
    }

    const result = await db.query(
      `SELECT 
         COUNT(f.id) as total_feedback,
         AVG(f.rating) as average_rating,
         COUNT(CASE WHEN f.rating = 5 THEN 1 END) as five_star,
         COUNT(CASE WHEN f.rating = 4 THEN 1 END) as four_star,
         COUNT(CASE WHEN f.rating = 3 THEN 1 END) as three_star,
         COUNT(CASE WHEN f.rating = 2 THEN 1 END) as two_star,
         COUNT(CASE WHEN f.rating = 1 THEN 1 END) as one_star
       FROM feedback f
       JOIN swaps s ON f.swap_id = s.id
       WHERE (s.from_user_id = $1 OR s.to_user_id = $1) AND f.from_user != $1`,
      [userId]
    );

    const stats = result.rows[0];
    res.json({
      total_feedback: parseInt(stats.total_feedback),
      average_rating: parseFloat(stats.average_rating) || 0,
      rating_breakdown: {
        five_star: parseInt(stats.five_star),
        four_star: parseInt(stats.four_star),
        three_star: parseInt(stats.three_star),
        two_star: parseInt(stats.two_star),
        one_star: parseInt(stats.one_star)
      }
    });
  } catch (error) {
    console.error('Get user rating error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update feedback (only if no one else has seen it)
router.put('/:id', authenticateToken, validateFeedback, async (req, res) => {
  try {
    const { id } = req.params;
    const { rating, comment } = req.body;

    // Check if feedback exists and belongs to user
    const feedbackResult = await db.query(
      'SELECT * FROM feedback WHERE id = $1 AND from_user = $2',
      [id, req.user.id]
    );

    if (feedbackResult.rows.length === 0) {
      return res.status(404).json({ error: 'Feedback not found' });
    }

    const result = await db.query(
      `UPDATE feedback 
       SET rating = $1, comment = $2
       WHERE id = $3 AND from_user = $4
       RETURNING id, rating, comment, created_at`,
      [rating, comment, id, req.user.id]
    );

    res.json({
      message: 'Feedback updated successfully',
      feedback: result.rows[0]
    });
  } catch (error) {
    console.error('Update feedback error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router; 