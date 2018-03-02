# AutoQuiz
MS Project Demo, using flask

Simplified maintnance:

0. Initialize database by running "sh init_db.sh" on mac, or "sqlite3 auto_quiz.db < schema.sql" followed by "python init_db.py" in any other environment.

1. When adding a question to the system: (1) create a new file under ./static/dataset/ with the given format of other existing .xml files; (2) if involve new skill, log it in variable skill_map in init_db.py; (3) run script update_db_skill_question.py