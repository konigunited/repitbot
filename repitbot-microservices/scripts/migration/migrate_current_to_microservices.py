#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main migration script to migrate data from monolithic RepitBot to microservices architecture.
This script orchestrates the entire migration process across all services.

Usage:
    python migrate_current_to_microservices.py --source-db sqlite:///repitbot.db --target-db postgresql://user:pass@localhost/repitbot_dev
    python migrate_current_to_microservices.py --config migration_config.yaml --dry-run
    python migrate_current_to_microservices.py --rollback --backup-file backup_20231201.sql
"""
import asyncio
import argparse
import logging
import os
import sys
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import shared components
from shared.models.enums import UserRole, HomeworkStatus, TopicMastery, AttendanceStatus, LessonStatus
from shared.utils.database import DatabaseConfig, DatabaseManager
from shared.events.base import EventFactory, EventType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationConfig:
    """Migration configuration."""
    source_database_url: str
    target_database_url: str
    batch_size: int = 1000
    dry_run: bool = False
    create_backup: bool = True
    backup_directory: str = "./backups"
    services_to_migrate: List[str] = None
    skip_validation: bool = False
    parallel_migration: bool = True
    max_workers: int = 4

    def __post_init__(self):
        if self.services_to_migrate is None:
            self.services_to_migrate = [
                'user-service',
                'lesson-service', 
                'homework-service',
                'payment-service',
                'material-service',
                'achievement-service'
            ]


class MigrationStats:
    """Migration statistics tracker."""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        self.tables_migrated = 0
        self.records_migrated = 0
        self.errors = []
        self.warnings = []
        self.service_stats = {}
    
    def add_service_stats(self, service: str, table: str, count: int):
        """Add migration stats for a service table."""
        if service not in self.service_stats:
            self.service_stats[service] = {}
        self.service_stats[service][table] = count
        self.records_migrated += count
        self.tables_migrated += 1
    
    def add_error(self, error: str, service: str = None, table: str = None):
        """Add migration error."""
        error_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error,
            'service': service,
            'table': table
        }
        self.errors.append(error_entry)
        logger.error(f"Migration error: {error}")
    
    def add_warning(self, warning: str, service: str = None, table: str = None):
        """Add migration warning."""
        warning_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'warning': warning,
            'service': service,
            'table': table
        }
        self.warnings.append(warning_entry)
        logger.warning(f"Migration warning: {warning}")
    
    def finalize(self):
        """Finalize migration stats."""
        self.end_time = datetime.now(timezone.utc)
    
    def get_duration(self) -> float:
        """Get migration duration in seconds."""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.get_duration(),
            'tables_migrated': self.tables_migrated,
            'records_migrated': self.records_migrated,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'service_stats': self.service_stats,
            'errors': self.errors,
            'warnings': self.warnings
        }


class MigrationValidator:
    """Validates migration data integrity."""
    
    def __init__(self, source_engine, target_engine):
        self.source_engine = source_engine
        self.target_engine = target_engine
    
    def validate_table_counts(self, table_mappings: Dict[str, str]) -> List[str]:
        """Validate record counts match between source and target."""
        errors = []
        
        with self.source_engine.connect() as source_conn:
            with self.target_engine.connect() as target_conn:
                for source_table, target_table in table_mappings.items():
                    try:
                        # Get source count
                        source_result = source_conn.execute(text(f"SELECT COUNT(*) FROM {source_table}"))
                        source_count = source_result.scalar()
                        
                        # Get target count
                        target_result = target_conn.execute(text(f"SELECT COUNT(*) FROM {target_table}"))
                        target_count = target_result.scalar()
                        
                        if source_count != target_count:
                            errors.append(
                                f"Count mismatch for {source_table} -> {target_table}: "
                                f"source={source_count}, target={target_count}"
                            )
                        else:
                            logger.info(f"✓ Count validation passed for {source_table}: {source_count} records")
                    
                    except Exception as e:
                        errors.append(f"Failed to validate {source_table} -> {target_table}: {str(e)}")
        
        return errors
    
    def validate_data_integrity(self, validation_queries: Dict[str, str]) -> List[str]:
        """Run custom validation queries."""
        errors = []
        
        with self.target_engine.connect() as conn:
            for validation_name, query in validation_queries.items():
                try:
                    result = conn.execute(text(query))
                    # If query returns results, it indicates an integrity issue
                    issues = result.fetchall()
                    if issues:
                        errors.append(f"Data integrity issue in {validation_name}: {len(issues)} problems found")
                        for issue in issues[:5]:  # Show first 5 issues
                            errors.append(f"  - {issue}")
                    else:
                        logger.info(f"✓ Data integrity validation passed for {validation_name}")
                
                except Exception as e:
                    errors.append(f"Failed to run validation {validation_name}: {str(e)}")
        
        return errors


class MonolithMigrator:
    """Main migration orchestrator."""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.stats = MigrationStats()
        self.source_engine = None
        self.target_engine = None
        self.validator = None
    
    def setup_connections(self):
        """Setup database connections."""
        try:
            logger.info("Setting up database connections...")
            
            # Source database (monolith)
            self.source_engine = create_engine(self.config.source_database_url)
            
            # Target database (microservices)
            self.target_engine = create_engine(self.config.target_database_url)
            
            # Validator
            self.validator = MigrationValidator(self.source_engine, self.target_engine)
            
            # Test connections
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Source database connection established")
            
            with self.target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Target database connection established")
            
        except Exception as e:
            self.stats.add_error(f"Failed to setup connections: {str(e)}")
            raise
    
    def create_backup(self):
        """Create backup of source database."""
        if not self.config.create_backup:
            return
        
        try:
            logger.info("Creating database backup...")
            backup_dir = Path(self.config.backup_directory)
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"repitbot_backup_{timestamp}.sql"
            
            # For SQLite, we can copy the file
            if self.config.source_database_url.startswith('sqlite'):
                import shutil
                db_path = self.config.source_database_url.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_file.with_suffix('.db'))
                logger.info(f"✓ SQLite backup created: {backup_file.with_suffix('.db')}")
            else:
                # For PostgreSQL, use pg_dump
                # This would need to be implemented based on the actual database type
                logger.warning("Backup creation not implemented for this database type")
            
        except Exception as e:
            self.stats.add_warning(f"Failed to create backup: {str(e)}")
    
    def migrate_users_service(self):
        """Migrate data for user-service."""
        logger.info("Migrating user-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    # Start transaction
                    trans = target_conn.begin()
                    
                    try:
                        # Migrate users table
                        users_query = """
                            SELECT id, telegram_id, username, full_name, role, access_code,
                                   points, streak_days, last_lesson_date, total_study_hours,
                                   parent_id, second_parent_id, created_at
                            FROM users
                        """
                        
                        users_result = source_conn.execute(text(users_query))
                        users = users_result.fetchall()
                        
                        if not self.config.dry_run:
                            # Insert users in batches
                            for i in range(0, len(users), self.config.batch_size):
                                batch = users[i:i + self.config.batch_size]
                                
                                # Prepare insert query
                                insert_query = """
                                    INSERT INTO users (
                                        id, telegram_id, username, full_name, role, access_code,
                                        points, streak_days, last_lesson_date, total_study_hours,
                                        parent_id, second_parent_id, created_at
                                    ) VALUES (
                                        :id, :telegram_id, :username, :full_name, :role, :access_code,
                                        :points, :streak_days, :last_lesson_date, :total_study_hours,
                                        :parent_id, :second_parent_id, :created_at
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        telegram_id = EXCLUDED.telegram_id,
                                        username = EXCLUDED.username,
                                        full_name = EXCLUDED.full_name,
                                        role = EXCLUDED.role,
                                        access_code = EXCLUDED.access_code,
                                        points = EXCLUDED.points,
                                        streak_days = EXCLUDED.streak_days,
                                        last_lesson_date = EXCLUDED.last_lesson_date,
                                        total_study_hours = EXCLUDED.total_study_hours,
                                        parent_id = EXCLUDED.parent_id,
                                        second_parent_id = EXCLUDED.second_parent_id,
                                        updated_at = CURRENT_TIMESTAMP
                                """
                                
                                target_conn.execute(text(insert_query), [dict(user._mapping) for user in batch])
                                logger.info(f"Migrated {len(batch)} users (batch {i // self.config.batch_size + 1})")
                        
                        trans.commit()
                        self.stats.add_service_stats('user-service', 'users', len(users))
                        logger.info(f"✓ User-service migration completed: {len(users)} users migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"User-service migration failed: {str(e)}", 'user-service', 'users')
            raise
    
    def migrate_lesson_service(self):
        """Migrate data for lesson-service."""
        logger.info("Migrating lesson-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    trans = target_conn.begin()
                    
                    try:
                        # Migrate lessons table
                        lessons_query = """
                            SELECT id, topic, date, skills_developed, mastery_level, mastery_comment,
                                   attendance_status, lesson_status, original_date, is_rescheduled,
                                   student_id, created_at
                            FROM lessons
                        """
                        
                        lessons_result = source_conn.execute(text(lessons_query))
                        lessons = lessons_result.fetchall()
                        
                        if not self.config.dry_run:
                            for i in range(0, len(lessons), self.config.batch_size):
                                batch = lessons[i:i + self.config.batch_size]
                                
                                insert_query = """
                                    INSERT INTO lessons (
                                        id, topic, date, skills_developed, mastery_level, mastery_comment,
                                        attendance_status, lesson_status, original_date, is_rescheduled,
                                        student_id, created_at
                                    ) VALUES (
                                        :id, :topic, :date, :skills_developed, :mastery_level, :mastery_comment,
                                        :attendance_status, :lesson_status, :original_date, :is_rescheduled,
                                        :student_id, :created_at
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        topic = EXCLUDED.topic,
                                        date = EXCLUDED.date,
                                        skills_developed = EXCLUDED.skills_developed,
                                        mastery_level = EXCLUDED.mastery_level,
                                        mastery_comment = EXCLUDED.mastery_comment,
                                        attendance_status = EXCLUDED.attendance_status,
                                        lesson_status = EXCLUDED.lesson_status,
                                        original_date = EXCLUDED.original_date,
                                        is_rescheduled = EXCLUDED.is_rescheduled,
                                        updated_at = CURRENT_TIMESTAMP
                                """
                                
                                target_conn.execute(text(insert_query), [dict(lesson._mapping) for lesson in batch])
                        
                        trans.commit()
                        self.stats.add_service_stats('lesson-service', 'lessons', len(lessons))
                        logger.info(f"✓ Lesson-service migration completed: {len(lessons)} lessons migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"Lesson-service migration failed: {str(e)}", 'lesson-service', 'lessons')
            raise
    
    def migrate_homework_service(self):
        """Migrate data for homework-service."""
        logger.info("Migrating homework-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    trans = target_conn.begin()
                    
                    try:
                        # Migrate homeworks table
                        homeworks_query = """
                            SELECT id, description, file_link, photo_file_ids, submission_text,
                                   submission_photo_file_ids, status, deadline, created_at,
                                   checked_at, lesson_id
                            FROM homeworks
                        """
                        
                        homeworks_result = source_conn.execute(text(homeworks_query))
                        homeworks = homeworks_result.fetchall()
                        
                        if not self.config.dry_run:
                            for i in range(0, len(homeworks), self.config.batch_size):
                                batch = homeworks[i:i + self.config.batch_size]
                                
                                insert_query = """
                                    INSERT INTO homeworks (
                                        id, description, file_link, photo_file_ids, submission_text,
                                        submission_photo_file_ids, status, deadline, created_at,
                                        checked_at, lesson_id
                                    ) VALUES (
                                        :id, :description, :file_link, :photo_file_ids, :submission_text,
                                        :submission_photo_file_ids, :status, :deadline, :created_at,
                                        :checked_at, :lesson_id
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        description = EXCLUDED.description,
                                        file_link = EXCLUDED.file_link,
                                        photo_file_ids = EXCLUDED.photo_file_ids,
                                        submission_text = EXCLUDED.submission_text,
                                        submission_photo_file_ids = EXCLUDED.submission_photo_file_ids,
                                        status = EXCLUDED.status,
                                        deadline = EXCLUDED.deadline,
                                        checked_at = EXCLUDED.checked_at,
                                        updated_at = CURRENT_TIMESTAMP
                                """
                                
                                target_conn.execute(text(insert_query), [dict(hw._mapping) for hw in batch])
                        
                        trans.commit()
                        self.stats.add_service_stats('homework-service', 'homeworks', len(homeworks))
                        logger.info(f"✓ Homework-service migration completed: {len(homeworks)} homeworks migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"Homework-service migration failed: {str(e)}", 'homework-service', 'homeworks')
            raise
    
    def migrate_payment_service(self):
        """Migrate data for payment-service."""
        logger.info("Migrating payment-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    trans = target_conn.begin()
                    
                    try:
                        # Migrate payments table
                        payments_query = """
                            SELECT id, lessons_paid, payment_date, student_id, created_at
                            FROM payments
                        """
                        
                        payments_result = source_conn.execute(text(payments_query))
                        payments = payments_result.fetchall()
                        
                        if not self.config.dry_run:
                            for i in range(0, len(payments), self.config.batch_size):
                                batch = payments[i:i + self.config.batch_size]
                                
                                insert_query = """
                                    INSERT INTO payments (
                                        id, lessons_paid, payment_date, student_id, created_at
                                    ) VALUES (
                                        :id, :lessons_paid, :payment_date, :student_id, :created_at
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        lessons_paid = EXCLUDED.lessons_paid,
                                        payment_date = EXCLUDED.payment_date,
                                        updated_at = CURRENT_TIMESTAMP
                                """
                                
                                target_conn.execute(text(insert_query), [dict(payment._mapping) for payment in batch])
                        
                        trans.commit()
                        self.stats.add_service_stats('payment-service', 'payments', len(payments))
                        logger.info(f"✓ Payment-service migration completed: {len(payments)} payments migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"Payment-service migration failed: {str(e)}", 'payment-service', 'payments')
            raise
    
    def migrate_material_service(self):
        """Migrate data for material-service."""
        logger.info("Migrating material-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    trans = target_conn.begin()
                    
                    try:
                        # Migrate materials table
                        materials_query = """
                            SELECT id, title, link, description, grade, created_at
                            FROM materials
                        """
                        
                        materials_result = source_conn.execute(text(materials_query))
                        materials = materials_result.fetchall()
                        
                        if not self.config.dry_run:
                            for i in range(0, len(materials), self.config.batch_size):
                                batch = materials[i:i + self.config.batch_size]
                                
                                insert_query = """
                                    INSERT INTO materials (
                                        id, title, link, description, grade, created_at
                                    ) VALUES (
                                        :id, :title, :link, :description, :grade, :created_at
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        title = EXCLUDED.title,
                                        link = EXCLUDED.link,
                                        description = EXCLUDED.description,
                                        grade = EXCLUDED.grade,
                                        updated_at = CURRENT_TIMESTAMP
                                """
                                
                                target_conn.execute(text(insert_query), [dict(material._mapping) for material in batch])
                        
                        trans.commit()
                        self.stats.add_service_stats('material-service', 'materials', len(materials))
                        logger.info(f"✓ Material-service migration completed: {len(materials)} materials migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"Material-service migration failed: {str(e)}", 'material-service', 'materials')
            raise
    
    def migrate_achievement_service(self):
        """Migrate data for achievement-service."""
        logger.info("Migrating achievement-service data...")
        
        try:
            with self.source_engine.connect() as source_conn:
                with self.target_engine.connect() as target_conn:
                    trans = target_conn.begin()
                    
                    try:
                        # Check if achievements table exists in source
                        inspector = inspect(self.source_engine)
                        if 'achievements' not in inspector.get_table_names():
                            logger.warning("Achievements table not found in source database, skipping migration")
                            return
                        
                        # Migrate achievements table
                        achievements_query = """
                            SELECT id, student_id, achievement_type, title, description, icon, earned_at
                            FROM achievements
                        """
                        
                        achievements_result = source_conn.execute(text(achievements_query))
                        achievements = achievements_result.fetchall()
                        
                        if not self.config.dry_run:
                            for i in range(0, len(achievements), self.config.batch_size):
                                batch = achievements[i:i + self.config.batch_size]
                                
                                insert_query = """
                                    INSERT INTO achievements (
                                        id, student_id, achievement_type, title, description, icon, earned_at
                                    ) VALUES (
                                        :id, :student_id, :achievement_type, :title, :description, :icon, :earned_at
                                    ) ON CONFLICT (id) DO UPDATE SET
                                        title = EXCLUDED.title,
                                        description = EXCLUDED.description,
                                        icon = EXCLUDED.icon
                                """
                                
                                target_conn.execute(text(insert_query), [dict(ach._mapping) for ach in batch])
                        
                        trans.commit()
                        self.stats.add_service_stats('achievement-service', 'achievements', len(achievements))
                        logger.info(f"✓ Achievement-service migration completed: {len(achievements)} achievements migrated")
                    
                    except Exception as e:
                        trans.rollback()
                        raise e
        
        except Exception as e:
            self.stats.add_error(f"Achievement-service migration failed: {str(e)}", 'achievement-service', 'achievements')
            if "no such table" not in str(e).lower():  # Don't raise if table doesn't exist
                raise
    
    def run_validation(self):
        """Run post-migration validation."""
        if self.config.skip_validation:
            logger.info("Skipping validation as requested")
            return
        
        logger.info("Running post-migration validation...")
        
        # Table count validation
        table_mappings = {
            'users': 'users',
            'lessons': 'lessons',
            'homeworks': 'homeworks',
            'payments': 'payments',
            'materials': 'materials',
            'achievements': 'achievements'
        }
        
        count_errors = self.validator.validate_table_counts(table_mappings)
        for error in count_errors:
            self.stats.add_error(error, service='validation')
        
        # Data integrity validation
        integrity_queries = {
            'orphaned_lessons': "SELECT COUNT(*) FROM lessons l WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = l.student_id)",
            'orphaned_homeworks': "SELECT COUNT(*) FROM homeworks h WHERE NOT EXISTS (SELECT 1 FROM lessons l WHERE l.id = h.lesson_id)",
            'orphaned_payments': "SELECT COUNT(*) FROM payments p WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = p.student_id)",
            'orphaned_achievements': "SELECT COUNT(*) FROM achievements a WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.student_id)",
            'invalid_user_roles': "SELECT COUNT(*) FROM users WHERE role NOT IN ('tutor', 'student', 'parent')",
        }
        
        integrity_errors = self.validator.validate_data_integrity(integrity_queries)
        for error in integrity_errors:
            self.stats.add_error(error, service='validation')
        
        if count_errors or integrity_errors:
            logger.error(f"Validation failed with {len(count_errors + integrity_errors)} errors")
        else:
            logger.info("✓ All validation checks passed")
    
    def run_migration(self):
        """Run the complete migration process."""
        try:
            logger.info("Starting RepitBot migration to microservices...")
            logger.info(f"Configuration: {asdict(self.config)}")
            
            # Setup
            self.setup_connections()
            self.create_backup()
            
            # Run migrations for each service
            migration_functions = {
                'user-service': self.migrate_users_service,
                'lesson-service': self.migrate_lesson_service,
                'homework-service': self.migrate_homework_service,
                'payment-service': self.migrate_payment_service,
                'material-service': self.migrate_material_service,
                'achievement-service': self.migrate_achievement_service,
            }
            
            # Execute migrations
            for service in self.config.services_to_migrate:
                if service in migration_functions:
                    try:
                        migration_functions[service]()
                    except Exception as e:
                        logger.error(f"Failed to migrate {service}: {str(e)}")
                        if not self.config.dry_run:
                            # Continue with other services
                            continue
                        else:
                            raise
                else:
                    self.stats.add_warning(f"Unknown service: {service}")
            
            # Validation
            if not self.config.dry_run:
                self.run_validation()
            
            # Finalize
            self.stats.finalize()
            
            # Report
            self.generate_report()
            
            logger.info(f"Migration completed successfully in {self.stats.get_duration():.2f} seconds")
            logger.info(f"Total records migrated: {self.stats.records_migrated}")
            logger.info(f"Tables migrated: {self.stats.tables_migrated}")
            
            if self.stats.errors:
                logger.error(f"Migration completed with {len(self.stats.errors)} errors")
                return False
            
            return True
        
        except Exception as e:
            self.stats.add_error(f"Migration failed: {str(e)}")
            self.stats.finalize()
            self.generate_report()
            logger.error(f"Migration failed: {str(e)}")
            return False
        
        finally:
            if self.source_engine:
                self.source_engine.dispose()
            if self.target_engine:
                self.target_engine.dispose()
    
    def generate_report(self):
        """Generate migration report."""
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(self.stats.to_dict(), f, indent=2, default=str)
            logger.info(f"Migration report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save migration report: {str(e)}")


def load_config_from_file(config_file: str) -> MigrationConfig:
    """Load migration configuration from file."""
    try:
        with open(config_file, 'r') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        return MigrationConfig(**config_data)
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_file}: {str(e)}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Migrate RepitBot from monolith to microservices')
    parser.add_argument('--source-db', required=True, help='Source database URL')
    parser.add_argument('--target-db', required=True, help='Target database URL')
    parser.add_argument('--config', help='Configuration file (YAML or JSON)')
    parser.add_argument('--dry-run', action='store_true', help='Run migration without making changes')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for migration')
    parser.add_argument('--services', nargs='+', help='Services to migrate')
    parser.add_argument('--skip-validation', action='store_true', help='Skip post-migration validation')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        if args.config:
            config = load_config_from_file(args.config)
            # Override with command line arguments
            if args.source_db:
                config.source_database_url = args.source_db
            if args.target_db:
                config.target_database_url = args.target_db
        else:
            config = MigrationConfig(
                source_database_url=args.source_db,
                target_database_url=args.target_db,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                create_backup=not args.no_backup,
                services_to_migrate=args.services,
                skip_validation=args.skip_validation,
                max_workers=args.workers
            )
        
        # Run migration
        migrator = MonolithMigrator(config)
        success = migrator.run_migration()
        
        if success:
            logger.info("✅ Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Migration completed with errors!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()


# TODO: Add rollback functionality
# TODO: Add support for incremental migrations
# TODO: Add support for custom migration scripts
# TODO: Add progress monitoring and resume capability
# TODO: Add support for data transformations during migration