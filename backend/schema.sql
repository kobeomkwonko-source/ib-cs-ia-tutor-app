-- Schema updates for tutor_app homework system

ALTER TABLE users
  ADD COLUMN email VARCHAR(255) NULL UNIQUE AFTER username,
  MODIFY COLUMN points INT NOT NULL DEFAULT 0;

ALTER TABLE tasks
  ADD COLUMN points INT NOT NULL DEFAULT 0 AFTER description,
  ADD COLUMN difficulty ENUM('easy','medium','hard') NOT NULL DEFAULT 'medium' AFTER points,
  ADD COLUMN created_by INT NULL AFTER deadline,
  ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER created_by,
  ADD COLUMN updated_at DATETIME NULL DEFAULT NULL AFTER created_at;

CREATE TABLE IF NOT EXISTS submissions (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  task_id INT NOT NULL,
  student_id INT NOT NULL,
  submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  text_content TEXT NULL,
  pdf_path VARCHAR(255) NULL,
  teacher_comment TEXT NULL,
  awarded_points INT NULL,
  awarded_at DATETIME NULL,
  CONSTRAINT fk_submissions_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_submissions_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_submissions_task (task_id),
  INDEX idx_submissions_student (student_id)
);

CREATE TABLE IF NOT EXISTS rewards (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  cost INT NOT NULL DEFAULT 0,
  created_by INT NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL DEFAULT NULL,
  CONSTRAINT fk_rewards_teacher FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS purchases (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  reward_id INT NOT NULL,
  student_id INT NOT NULL,
  purchased_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cost_at_purchase INT NOT NULL,
  CONSTRAINT fk_purchases_reward FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE,
  CONSTRAINT fk_purchases_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_purchases_student (student_id)
);

CREATE TABLE IF NOT EXISTS reminder_logs (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  task_id INT NOT NULL,
  student_id INT NOT NULL,
  reminder_type ENUM('24h','12h') NOT NULL,
  sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_reminder_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_reminder_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_reminder (task_id, student_id, reminder_type)
);

CREATE TABLE IF NOT EXISTS task_assignments (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  task_id INT NOT NULL,
  student_id INT NOT NULL,
  assigned_by INT NOT NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_assignment_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_assignment_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_assignment_teacher FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_task_assignment (task_id, student_id),
  INDEX idx_task_assignments_task (task_id),
  INDEX idx_task_assignments_student (student_id)
);
