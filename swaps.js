const express = require('express');
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');
const { validateSwap, validateSwapUpdate } = require('../middleware/validation');

const router = express.Router();

// Create a new swap request
router.post('/', authenticateToken, validateSwap, async (req, res) => {
  try {
    const { to_user_id, skill_offered_us, skill_requested_us } = req.body;

    // Check if target user exists and is public
    const targetUser = await db.query(
      'SELECT id FROM users WHERE id = $1 AND is_public = true',
      [to_user_id]
    );

    if (targetUser.rows.length === 0) {
      return res.status(404).json({ error: 'Target user not found or profile is private' });
    }

    // Check if user is trying to swap with themselves
    if (to_user_id === req.user.id) {
      return res.status(400).json({ error: 'Cannot create swap with yourself' });
    }

    // Verify that the offered skill belongs to the current user
    const offeredSkill = await db.query(
      'SELECT id FROM user_skills WHERE id = $1 AND user_id = $2',
      [skill_offered_us, req.user.id]
    );

    if (offeredSkill.rows.length === 0) {
      return res.status(400).json({ error: 'Offered skill not found or does not belong to you' });
    }

    // Verify that the requested skill belongs to the target user
    const requestedSkill = await db.query(
      'SELECT id FROM user_skills WHERE id = $1 AND user_id = $2',
      [skill_requested_us, to_user_id]
    );

    if (requestedSkill.rows.length === 0) {
      return res.status(400).json({ error: 'Requested skill not found or does not belong to target user' });
    }

    // Check if there's already a pending swap between these users with these skills
    const existingSwap = await db.query(
      `SELECT id FROM swaps 
       WHERE ((from_user_id = $1 AND to_user_id = $2) OR (from_user_id = $2 AND to_user_id = $1))
       AND skill_offered_us = $3 AND skill_requested_us = $4
       AND status = 'pending'`,
      [req.user.id, to_user_id, skill_offered_us, skill_requested_us]
    );

    if (existingSwap.rows.length > 0) {
      return res.status(400).json({ error: 'A pending swap with these skills already exists' });
    }

    const result = await db.query(
      `INSERT INTO swaps (from_user_id, to_user_id, skill_offered_us, skill_requested_us, status)
       VALUES ($1, $2, $3, $4, 'pending')
       RETURNING id, from_user_id, to_user_id, skill_offered_us, skill_requested_us, status, created_at`,
      [req.user.id, to_user_id, skill_offered_us, skill_requested_us]
    );

    res.status(201).json({
      message: 'Swap request created successfully',
      swap: result.rows[0]
    });
  } catch (error) {
    console.error('Create swap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user's swaps (sent and received)
router.get('/', authenticateToken, async (req, res) => {
  try {
    const { status } = req.query;
    
    let query = `
      SELECT s.id, s.status, s.created_at, s.updated_at,
             s.from_user_id, s.to_user_id,
             s.skill_offered_us, s.skill_requested_us,
             from_user.name as from_user_name,
             to_user.name as to_user_name,
             offered_skill.description as offered_description,
             offered_skill.skill_level as offered_skill_level,
             requested_skill.description as requested_description,
             requested_skill.skill_level as requested_skill_level,
             offered_skill_s.name as offered_skill_name,
             requested_skill_s.name as requested_skill_name
      FROM swaps s
      JOIN users from_user ON s.from_user_id = from_user.id
      JOIN users to_user ON s.to_user_id = to_user.id
      JOIN user_skills offered_skill ON s.skill_offered_us = offered_skill.id
      JOIN user_skills requested_skill ON s.skill_requested_us = requested_skill.id
      JOIN skills offered_skill_s ON offered_skill.skill_id = offered_skill_s.id
      JOIN skills requested_skill_s ON requested_skill.skill_id = requested_skill_s.id
      WHERE s.from_user_id = $1 OR s.to_user_id = $1
    `;
    let values = [req.user.id];

    if (status) {
      query += ' AND s.status = $2';
      values.push(status);
    }

    query += ' ORDER BY s.created_at DESC';

    const result = await db.query(query, values);

    res.json({ swaps: result.rows });
  } catch (error) {
    console.error('Get swaps error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get specific swap by ID
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;

    const result = await db.query(
      `SELECT s.id, s.status, s.created_at, s.updated_at,
              s.from_user_id, s.to_user_id,
              s.skill_offered_us, s.skill_requested_us,
              from_user.name as from_user_name,
              to_user.name as to_user_name,
              offered_skill.description as offered_description,
              offered_skill.skill_level as offered_skill_level,
              requested_skill.description as requested_description,
              requested_skill.skill_level as requested_skill_level,
              offered_skill_s.name as offered_skill_name,
              requested_skill_s.name as requested_skill_name
       FROM swaps s
       JOIN users from_user ON s.from_user_id = from_user.id
       JOIN users to_user ON s.to_user_id = to_user.id
       JOIN user_skills offered_skill ON s.skill_offered_us = offered_skill.id
       JOIN user_skills requested_skill ON s.skill_requested_us = requested_skill.id
       JOIN skills offered_skill_s ON offered_skill.skill_id = offered_skill_s.id
       JOIN skills requested_skill_s ON requested_skill.skill_id = requested_skill_s.id
       WHERE s.id = $1 AND (s.from_user_id = $2 OR s.to_user_id = $2)`,
      [id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found' });
    }

    res.json({ swap: result.rows[0] });
  } catch (error) {
    console.error('Get swap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update swap status (accept/reject/cancel)
router.put('/:id/status', authenticateToken, validateSwapUpdate, async (req, res) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    // Get the swap
    const swapResult = await db.query(
      'SELECT * FROM swaps WHERE id = $1',
      [id]
    );

    if (swapResult.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found' });
    }

    const swap = swapResult.rows[0];

    // Check if user is authorized to update this swap
    if (swap.from_user_id !== req.user.id && swap.to_user_id !== req.user.id) {
      return res.status(403).json({ error: 'Not authorized to update this swap' });
    }

    // Check if swap can be updated
    if (swap.status !== 'pending') {
      return res.status(400).json({ error: 'Can only update pending swaps' });
    }

    // Only the recipient can accept/reject, sender can cancel
    if (status === 'accepted' || status === 'rejected') {
      if (swap.to_user_id !== req.user.id) {
        return res.status(403).json({ error: 'Only the recipient can accept or reject a swap' });
      }
    } else if (status === 'cancelled') {
      if (swap.from_user_id !== req.user.id) {
        return res.status(403).json({ error: 'Only the sender can cancel a swap' });
      }
    }

    const result = await db.query(
      `UPDATE swaps 
       SET status = $1, updated_at = NOW()
       WHERE id = $2
       RETURNING id, status, updated_at`,
      [status, id]
    );

    res.json({
      message: `Swap ${status} successfully`,
      swap: result.rows[0]
    });
  } catch (error) {
    console.error('Update swap status error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get potential swaps (users who want what you offer and offer what you want)
router.get('/potential/matches', authenticateToken, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT DISTINCT
        u.id, u.name, u.bio, u.location, u.photo_url, u.availability,
        offered_skill.description as offered_description,
        offered_skill.skill_level as offered_skill_level,
        wanted_skill.description as wanted_description,
        wanted_skill.skill_level as wanted_skill_level,
        offered_skill_s.name as offered_skill_name,
        wanted_skill_s.name as wanted_skill_name
       FROM users u
       JOIN user_skills offered_skill ON u.id = offered_skill.user_id
       JOIN user_skills wanted_skill ON u.id = wanted_skill.user_id
       JOIN skills offered_skill_s ON offered_skill.skill_id = offered_skill_s.id
       JOIN skills wanted_skill_s ON wanted_skill.skill_id = wanted_skill_s.id
       JOIN user_skills my_offered ON my_offered.user_id = $1 AND my_offered.role = 'offered'
       JOIN user_skills my_wanted ON my_wanted.user_id = $1 AND my_wanted.role = 'wanted'
       WHERE u.id != $1 
         AND u.is_public = true
         AND offered_skill.role = 'offered'
         AND wanted_skill.role = 'wanted'
         AND offered_skill.skill_id = my_wanted.skill_id
         AND wanted_skill.skill_id = my_offered.skill_id
       ORDER BY u.name`,
      [req.user.id]
    );

    res.json({ potentialMatches: result.rows });
  } catch (error) {
    console.error('Get potential matches error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router; 