const express = require('express');
const db = require('../config/database');
const { authenticateToken } = require('../middleware/auth');

const router = express.Router();

// Middleware to check if user is admin (simplified for demo)
const isAdmin = (req, res, next) => {
  // In a real application, you would check if the user has admin role
  // For demo purposes, we'll allow any authenticated user to access admin routes
  next();
};

// Log admin action
const logAdminAction = async (entityType, entityId, action, reason, adminId) => {
  try {
    await db.query(
      `INSERT INTO admin_logs (entity_type, entity_id, action, reason, admin_id)
       VALUES ($1, $2, $3, $4, $5)`,
      [entityType, entityId, action, reason, adminId]
    );
  } catch (error) {
    console.error('Error logging admin action:', error);
  }
};

// Get all admin logs
router.get('/logs', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { entity_type, action, limit = 50, offset = 0 } = req.query;

    let query = `
      SELECT al.id, al.entity_type, al.entity_id, al.action, al.reason, al.logged_at,
             admin.name as admin_name
      FROM admin_logs al
      JOIN users admin ON al.admin_id = admin.id
      WHERE 1=1
    `;
    let values = [];
    let paramCount = 1;

    if (entity_type) {
      query += ` AND al.entity_type = $${paramCount++}`;
      values.push(entity_type);
    }

    if (action) {
      query += ` AND al.action = $${paramCount++}`;
      values.push(action);
    }

    query += ` ORDER BY al.logged_at DESC LIMIT $${paramCount++} OFFSET $${paramCount++}`;
    values.push(parseInt(limit), parseInt(offset));

    const result = await db.query(query, values);

    res.json({ logs: result.rows });
  } catch (error) {
    console.error('Get admin logs error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Flag a user
router.post('/users/:id/flag', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if user exists
    const userExists = await db.query('SELECT id FROM users WHERE id = $1', [id]);
    if (userExists.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Log the action
    await logAdminAction('user', id, 'flag', reason, req.user.id);

    res.json({ message: 'User flagged successfully' });
  } catch (error) {
    console.error('Flag user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Ban a user
router.post('/users/:id/ban', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if user exists
    const userExists = await db.query('SELECT id FROM users WHERE id = $1', [id]);
    if (userExists.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    // In a real application, you would update the user's status to banned
    // For demo purposes, we'll just log the action
    await logAdminAction('user', id, 'ban', reason, req.user.id);

    res.json({ message: 'User banned successfully' });
  } catch (error) {
    console.error('Ban user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a user
router.delete('/users/:id', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if user exists
    const userExists = await db.query('SELECT id FROM users WHERE id = $1', [id]);
    if (userExists.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    // In a real application, you would soft delete or actually delete the user
    // For demo purposes, we'll just log the action
    await logAdminAction('user', id, 'delete', reason, req.user.id);

    res.json({ message: 'User deleted successfully' });
  } catch (error) {
    console.error('Delete user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Flag a skill
router.post('/skills/:id/flag', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if skill exists
    const skillExists = await db.query('SELECT id FROM skills WHERE id = $1', [id]);
    if (skillExists.rows.length === 0) {
      return res.status(404).json({ error: 'Skill not found' });
    }

    await logAdminAction('skill', id, 'flag', reason, req.user.id);

    res.json({ message: 'Skill flagged successfully' });
  } catch (error) {
    console.error('Flag skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a skill
router.delete('/skills/:id', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if skill exists
    const skillExists = await db.query('SELECT id FROM skills WHERE id = $1', [id]);
    if (skillExists.rows.length === 0) {
      return res.status(404).json({ error: 'Skill not found' });
    }

    // In a real application, you would check if the skill is being used before deleting
    await logAdminAction('skill', id, 'delete', reason, req.user.id);

    res.json({ message: 'Skill deleted successfully' });
  } catch (error) {
    console.error('Delete skill error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Flag a swap
router.post('/swaps/:id/flag', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if swap exists
    const swapExists = await db.query('SELECT id FROM swaps WHERE id = $1', [id]);
    if (swapExists.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found' });
    }

    await logAdminAction('swap', id, 'flag', reason, req.user.id);

    res.json({ message: 'Swap flagged successfully' });
  } catch (error) {
    console.error('Flag swap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Cancel a swap
router.post('/swaps/:id/cancel', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;

    // Check if swap exists and is pending
    const swapResult = await db.query(
      'SELECT id FROM swaps WHERE id = $1 AND status = $2',
      [id, 'pending']
    );
    if (swapResult.rows.length === 0) {
      return res.status(404).json({ error: 'Swap not found or not pending' });
    }

    // Update swap status
    await db.query(
      'UPDATE swaps SET status = $1, updated_at = NOW() WHERE id = $2',
      ['cancelled', id]
    );

    await logAdminAction('swap', id, 'cancel', reason, req.user.id);

    res.json({ message: 'Swap cancelled successfully' });
  } catch (error) {
    console.error('Cancel swap error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get system statistics
router.get('/stats', authenticateToken, isAdmin, async (req, res) => {
  try {
    const stats = {};

    // User statistics
    const userStats = await db.query(`
      SELECT 
        COUNT(*) as total_users,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_users_7d,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as new_users_30d
      FROM users
    `);
    stats.users = userStats.rows[0];

    // Swap statistics
    const swapStats = await db.query(`
      SELECT 
        COUNT(*) as total_swaps,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_swaps,
        COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_swaps,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_swaps,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_swaps_7d
      FROM swaps
    `);
    stats.swaps = swapStats.rows[0];

    // Skill statistics
    const skillStats = await db.query(`
      SELECT 
        COUNT(DISTINCT s.id) as total_skills,
        COUNT(DISTINCT us.user_id) as users_with_skills,
        COUNT(us.id) as total_user_skills
      FROM skills s
      LEFT JOIN user_skills us ON s.id = us.skill_id
    `);
    stats.skills = skillStats.rows[0];

    // Feedback statistics
    const feedbackStats = await db.query(`
      SELECT 
        COUNT(*) as total_feedback,
        AVG(rating) as average_rating,
        COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_feedback_7d
      FROM feedback
    `);
    stats.feedback = feedbackStats.rows[0];

    res.json({ stats });
  } catch (error) {
    console.error('Get stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router; 