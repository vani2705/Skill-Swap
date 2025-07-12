const express = require('express');
const bcrypt = require('bcryptjs');
const db = require('../config/database');
const { authenticateToken, generateToken } = require('../middleware/auth');
const { validateUserRegistration, validateUserLogin, validateUserUpdate } = require('../middleware/validation');

const router = express.Router();

// Register new user
router.post('/register', validateUserRegistration, async (req, res) => {
  try {
    const { name, email, password, bio, location, is_public, availability } = req.body;

    // Check if user already exists
    const existingUser = await db.query('SELECT id FROM users WHERE email = $1', [email]);
    if (existingUser.rows.length > 0) {
      return res.status(400).json({ error: 'User with this email already exists' });
    }

    // Hash password
    const saltRounds = 10;
    const passwordHash = await bcrypt.hash(password, saltRounds);

    // Insert new user
    const result = await db.query(
      `INSERT INTO users (name, email, password_hash, bio, location, is_public, availability)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id, name, email, bio, location, is_public, availability, created_at`,
      [name, email, passwordHash, bio, location, is_public, availability]
    );

    const user = result.rows[0];
    const token = generateToken(user.id);

    res.status(201).json({
      message: 'User registered successfully',
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        bio: user.bio,
        location: user.location,
        is_public: user.is_public,
        availability: user.availability,
        created_at: user.created_at
      },
      token
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Login user
router.post('/login', validateUserLogin, async (req, res) => {
  try {
    const { email, password } = req.body;

    // Find user by email
    const result = await db.query(
      'SELECT id, name, email, password_hash, bio, location, is_public, availability FROM users WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const user = result.rows[0];

    // Check password
    const isValidPassword = await bcrypt.compare(password, user.password_hash);
    if (!isValidPassword) {
      return res.status(401).json({ error: 'Invalid email or password' });
    }

    const token = generateToken(user.id);

    res.json({
      message: 'Login successful',
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        bio: user.bio,
        location: user.location,
        is_public: user.is_public,
        availability: user.availability
      },
      token
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get current user profile
router.get('/profile', authenticateToken, async (req, res) => {
  try {
    const result = await db.query(
      'SELECT id, name, email, bio, location, photo_url, is_public, availability, created_at FROM users WHERE id = $1',
      [req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ user: result.rows[0] });
  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user profile
router.put('/profile', authenticateToken, validateUserUpdate, async (req, res) => {
  try {
    const { name, bio, location, photo_url, is_public, availability } = req.body;
    
    const updateFields = [];
    const values = [];
    let paramCount = 1;

    if (name !== undefined) {
      updateFields.push(`name = $${paramCount++}`);
      values.push(name);
    }
    if (bio !== undefined) {
      updateFields.push(`bio = $${paramCount++}`);
      values.push(bio);
    }
    if (location !== undefined) {
      updateFields.push(`location = $${paramCount++}`);
      values.push(location);
    }
    if (photo_url !== undefined) {
      updateFields.push(`photo_url = $${paramCount++}`);
      values.push(photo_url);
    }
    if (is_public !== undefined) {
      updateFields.push(`is_public = $${paramCount++}`);
      values.push(is_public);
    }
    if (availability !== undefined) {
      updateFields.push(`availability = $${paramCount++}`);
      values.push(availability);
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(req.user.id);
    const query = `
      UPDATE users 
      SET ${updateFields.join(', ')}
      WHERE id = $${paramCount}
      RETURNING id, name, email, bio, location, photo_url, is_public, availability, created_at
    `;

    const result = await db.query(query, values);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({
      message: 'Profile updated successfully',
      user: result.rows[0]
    });
  } catch (error) {
    console.error('Update profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get public user profile by ID
router.get('/users/:id', async (req, res) => {
  try {
    const { id } = req.params;

    const result = await db.query(
      `SELECT id, name, bio, location, photo_url, availability, created_at
       FROM users 
       WHERE id = $1 AND is_public = true`,
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found or profile is private' });
    }

    res.json({ user: result.rows[0] });
  } catch (error) {
    console.error('Get public user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router; 