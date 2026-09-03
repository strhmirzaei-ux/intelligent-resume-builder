from app.db.models import Base
from app.db.session import Database
from app.modules.gap_analysis.rules import NODE_WEIGHTS


def test_database_contains_graph_persistence_tables():
    assert set(Base.metadata.tables) == {
        "users",
        "resume_sessions",
        "chat_messages",
        "resume_versions",
        "resume_graph_nodes",
    }


def test_graph_node_weights_match_resume_graph():
    columns = {
        column.name for column in Base.metadata.tables["resume_graph_nodes"].columns
    }
    assert {"node_key", "weight", "score", "missing_fields", "node_data"} <= columns
    assert NODE_WEIGHTS == {
        "personal_info": 1,
        "interactive_skills": 4,
        "projects": 3,
        "education": 2,
        "work_experience": 3,
    }


def test_database_session_is_a_context_manager():
    database = Database("sqlite+pysqlite:///:memory:")
    with database.session() as session:
        assert session.is_active
