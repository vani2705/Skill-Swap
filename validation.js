const { body, validationResult } = require('express-validator');

const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ 
      error: 'Validation failed',
      details: errors.array() 
    });
  }
  next();
};

// User validation rules
const validateUserRegistration = [
  body('name').trim().isLength({ min: 2, max: 100 }).withMessage('Name must be between 2 and 100 characters'),
  body('email').isEmail().normalizeEmail().withMessage('Valid email is required'),
  body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters long'),
  body('bio').optional().isLength({ max: 500 }).withMessage('Bio must be less than 500 characters'),
  body('is_public').optional().isBoolean().withMessage('Please select if your profile is public or not'),
  body('availability').optional().isArray().withMessage('Availability must be an array'),
  handleValidationErrors
];

const validateUserLogin = [
  body('email').isEmail().normalizeEmail().withMessage('Valid email is required'),
  body('password').notEmpty().withMessage('Password is required'),
  handleValidationErrors
];

const validateUserUpdate = [
  body('name').optional().trim().isLength({ min: 2, max: 100 }).withMessage('Name must be between 2 and 100 characters'),
  body('bio').optional().isLength({ max: 500 }).withMessage('Bio must be less than 500 characters'),
  body('is_public').optional().isBoolean().withMessage('is_public must be a boolean'),
  body('availability').optional().isArray().withMessage('Availability must be an array'),
  handleValidationErrors
];

// Skill validation rules
const validateSkill = [
  body('name').trim().isLength({ min: 1, max: 50 }).withMessage('Skill name must be between 1 and 50 characters'),
  body('category').trim().isLength({ min: 1, max: 30 }).withMessage('Category must be between 1 and 30 characters'),
  handleValidationErrors
];

// User skill validation rules
const validateUserSkill = [
  body('skill_id').isInt({ min: 1 }).withMessage('Valid skill_id is required'),
  body('role').isIn(['offered', 'wanted']).withMessage('Role must be either "offered" or "wanted"'),
  body('skill_level').optional().isIn(['Beginner', 'Intermediate', 'Advanced', 'Expert']).withMessage('Skill level must be Beginner, Intermediate, Advanced, or Expert'),
  body('description').optional().isLength({ max: 300 }).withMessage('Description must be less than 300 characters'),
  handleValidationErrors
];

// Swap validation rules
const validateSwap = [
  body('to_user_id').isInt({ min: 1 }).withMessage('Valid to_user_id is required'),
  body('skill_offered_us').isInt({ min: 1 }).withMessage('Valid skill_offered_us is required'),
  body('skill_requested_us').isInt({ min: 1 }).withMessage('Valid skill_requested_us is required'),
  handleValidationErrors
];

const validateSwapUpdate = [
  body('status').isIn(['pending', 'accepted', 'rejected', 'cancelled']).withMessage('Invalid status'),
  handleValidationErrors
];

// Feedback validation rules
const validateFeedback = [
  body('swap_id').isInt({ min: 1 }).withMessage('Valid swap_id is required'),
  body('rating').isInt({ min: 1, max: 5 }).withMessage('Rating must be between 1 and 5'),
  body('comment').optional().isLength({ max: 500 }).withMessage('Comment must be less than 500 characters'),
  handleValidationErrors
];

module.exports = {
  handleValidationErrors,
  validateUserRegistration,
  validateUserLogin,
  validateUserUpdate,
  validateSkill,
  validateUserSkill,
  validateSwap,
  validateSwapUpdate,
  validateFeedback
}; 