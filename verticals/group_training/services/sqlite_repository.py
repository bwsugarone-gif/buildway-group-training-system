"""SQLite persistence for Phase 1.1 group training MVP."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from verticals.group_training.models import (
    AITrainingReview,
    ClosingScore,
    Customer,
    CustomerFollowup,
    CustomerStage,
    DailyActivityLog,
    Team,
    User,
    UserRole,
)
from verticals.group_training.services.auth_service import hash_password


DEFAULT_TENANT_ID = "tenant_buildway_demo"
DEFAULT_TEAM_ID = "team_alpha"


def default_sqlite_path() -> Path:
    return Path(__file__).resolve().parents[3] / "database" / "group_training.sqlite3"


def _date_to_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_to_text(value: datetime | None) -> str:
    return (value or datetime.utcnow()).isoformat(timespec="seconds")


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_datetime(value: str | None) -> datetime:
    return datetime.fromisoformat(value) if value else datetime.utcnow()


class SQLiteGroupTrainingRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_sqlite_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_access_if_empty()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    team_id TEXT,
                    manager_id TEXT,
                    password_hash TEXT NOT NULL,
                    UNIQUE (tenant_id, email)
                );

                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    manager_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    phone TEXT,
                    notes TEXT,
                    next_meeting_date TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS customer_followups (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    next_action TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_activity_logs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    activity_date TEXT NOT NULL,
                    call_count INTEGER NOT NULL,
                    whatsapp_count INTEGER NOT NULL,
                    appointment_count INTEGER NOT NULL,
                    meeting_count INTEGER NOT NULL,
                    closing_count INTEGER NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_training_reviews (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    review_date TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    improvement_advice TEXT NOT NULL,
                    manager_feedback TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS closing_scores (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    score_date TEXT NOT NULL,
                    hidden_score INTEGER NOT NULL,
                    rationale TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_gt_users_tenant_email ON users(tenant_id, email);
                CREATE INDEX IF NOT EXISTS idx_gt_customers_tenant_agent ON customers(tenant_id, agent_id);
                CREATE INDEX IF NOT EXISTS idx_gt_followups_customer ON customer_followups(tenant_id, customer_id);
                CREATE INDEX IF NOT EXISTS idx_gt_logs_tenant_agent_date ON daily_activity_logs(tenant_id, agent_id, activity_date);
                CREATE INDEX IF NOT EXISTS idx_gt_reviews_tenant_agent_date ON ai_training_reviews(tenant_id, agent_id, review_date);
                CREATE INDEX IF NOT EXISTS idx_gt_scores_tenant_agent_date ON closing_scores(tenant_id, agent_id, score_date);
                """
            )

    def _seed_access_if_empty(self) -> None:
        with self._connect() as conn:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count:
            return
        self.add_user(
            User(
                DEFAULT_TENANT_ID,
                "admin_001",
                "Admin",
                "admin@buildway.demo",
                UserRole.ADMIN,
                password_hash=hash_password("Admin123!"),
            )
        )
        self.add_user(
            User(
                DEFAULT_TENANT_ID,
                "mgr_001",
                "Manager",
                "manager@buildway.demo",
                UserRole.MANAGER,
                DEFAULT_TEAM_ID,
                password_hash=hash_password("Manager123!"),
            )
        )
        self.add_user(
            User(
                DEFAULT_TENANT_ID,
                "agt_001",
                "Agent",
                "agent@buildway.demo",
                UserRole.AGENT,
                DEFAULT_TEAM_ID,
                "mgr_001",
                hash_password("Agent123!"),
            )
        )
        self.add_team(Team(DEFAULT_TENANT_ID, DEFAULT_TEAM_ID, "Alpha Insurance Team", "mgr_001"))

    def add_user(self, user: User) -> User:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO users
                (id, tenant_id, name, email, role, team_id, manager_id, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.tenant_id,
                    user.name,
                    user.email.lower(),
                    user.role.value,
                    user.team_id,
                    user.manager_id,
                    user.password_hash,
                ),
            )
        return user

    def add_team(self, team: Team) -> Team:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO teams
                (id, tenant_id, name, manager_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (team.id, team.tenant_id, team.name, team.manager_id, _datetime_to_text(team.created_at)),
            )
        return team

    def add_customer(self, customer: Customer) -> Customer:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO customers
                (id, tenant_id, team_id, agent_id, name, stage, phone, notes, next_meeting_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer.id,
                    customer.tenant_id,
                    customer.team_id,
                    customer.agent_id,
                    customer.name,
                    customer.stage.value,
                    customer.phone,
                    customer.notes,
                    _date_to_text(customer.next_meeting_date),
                    _datetime_to_text(customer.created_at),
                ),
            )
        return customer

    def add_followup(self, followup: CustomerFollowup) -> CustomerFollowup:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO customer_followups
                (id, tenant_id, customer_id, agent_id, note, next_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    followup.id,
                    followup.tenant_id,
                    followup.customer_id,
                    followup.agent_id,
                    followup.note,
                    followup.next_action,
                    _datetime_to_text(followup.created_at),
                ),
            )
        return followup

    def add_daily_log(self, log: DailyActivityLog) -> DailyActivityLog:
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM daily_activity_logs
                WHERE tenant_id = ? AND agent_id = ? AND activity_date = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (log.tenant_id, log.agent_id, _date_to_text(log.activity_date)),
            ).fetchone()
            duplicate_ids = conn.execute(
                """
                SELECT id FROM daily_activity_logs
                WHERE tenant_id = ? AND agent_id = ? AND activity_date = ?
                ORDER BY created_at DESC
                """,
                (log.tenant_id, log.agent_id, _date_to_text(log.activity_date)),
            ).fetchall()
            if existing:
                log.id = existing["id"]
                conn.execute(
                    """
                    UPDATE daily_activity_logs
                    SET team_id = ?, call_count = ?, whatsapp_count = ?, appointment_count = ?,
                        meeting_count = ?, closing_count = ?, notes = ?, created_at = ?
                    WHERE id = ?
                    """,
                    (
                        log.team_id,
                        log.call_count,
                        log.whatsapp_count,
                        log.appointment_count,
                        log.meeting_count,
                        log.closing_count,
                        log.notes,
                        _datetime_to_text(log.created_at),
                        log.id,
                    ),
                )
                stale_ids = [row["id"] for row in duplicate_ids if row["id"] != log.id]
                if stale_ids:
                    conn.executemany("DELETE FROM daily_activity_logs WHERE id = ?", [(row_id,) for row_id in stale_ids])
            else:
                conn.execute(
                    """
                    INSERT INTO daily_activity_logs
                    (id, tenant_id, team_id, agent_id, activity_date, call_count, whatsapp_count,
                     appointment_count, meeting_count, closing_count, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log.id,
                        log.tenant_id,
                        log.team_id,
                        log.agent_id,
                        _date_to_text(log.activity_date),
                        log.call_count,
                        log.whatsapp_count,
                        log.appointment_count,
                        log.meeting_count,
                        log.closing_count,
                        log.notes,
                        _datetime_to_text(log.created_at),
                    ),
                )
        return log

    def add_review(self, review: AITrainingReview) -> AITrainingReview:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM ai_training_reviews WHERE tenant_id = ? AND agent_id = ? AND review_date = ?",
                (review.tenant_id, review.agent_id, _date_to_text(review.review_date)),
            )
            conn.execute(
                """
                INSERT INTO ai_training_reviews
                (id, tenant_id, team_id, agent_id, review_date, summary, improvement_advice,
                 manager_feedback, risk_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review.id,
                    review.tenant_id,
                    review.team_id,
                    review.agent_id,
                    _date_to_text(review.review_date),
                    review.summary,
                    review.improvement_advice,
                    review.manager_feedback,
                    review.risk_level,
                    _datetime_to_text(review.created_at),
                ),
            )
        return review

    def add_closing_score(self, score: ClosingScore) -> ClosingScore:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM closing_scores WHERE tenant_id = ? AND agent_id = ? AND score_date = ?",
                (score.tenant_id, score.agent_id, _date_to_text(score.score_date)),
            )
            conn.execute(
                """
                INSERT INTO closing_scores
                (id, tenant_id, team_id, agent_id, score_date, hidden_score, rationale, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.id,
                    score.tenant_id,
                    score.team_id,
                    score.agent_id,
                    _date_to_text(score.score_date),
                    score.hidden_score,
                    score.rationale,
                    _datetime_to_text(score.created_at),
                ),
            )
        return score

    def list_users(self, tenant_id: str) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? ORDER BY role, email",
                (tenant_id,),
            ).fetchall()
        return [self._row_to_user(row) for row in rows]

    def get_user(self, tenant_id: str, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? AND id = ?",
                (tenant_id, user_id),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def find_user_by_email(self, tenant_id: str, email: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE tenant_id = ? AND email = ?",
                (tenant_id, email.strip().lower()),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def get_customer(self, tenant_id: str, customer_id: str) -> Customer | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE tenant_id = ? AND id = ?",
                (tenant_id, customer_id),
            ).fetchone()
        return self._row_to_customer(row) if row else None

    def list_agents_for_manager(self, tenant_id: str, manager_id: str) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM users
                WHERE tenant_id = ? AND role = ? AND manager_id = ?
                ORDER BY name
                """,
                (tenant_id, UserRole.AGENT.value, manager_id),
            ).fetchall()
        return [self._row_to_user(row) for row in rows]

    def list_customers(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        team_id: str | None = None,
    ) -> list[Customer]:
        sql = "SELECT * FROM customers WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        if team_id:
            sql += " AND team_id = ?"
            params.append(team_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_customer(row) for row in rows]

    def list_followups(self, tenant_id: str, customer_id: str | None = None) -> list[CustomerFollowup]:
        sql = "SELECT * FROM customer_followups WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if customer_id:
            sql += " AND customer_id = ?"
            params.append(customer_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_followup(row) for row in rows]

    def list_logs(
        self,
        tenant_id: str,
        activity_date: date | None = None,
        agent_id: str | None = None,
        team_id: str | None = None,
    ) -> list[DailyActivityLog]:
        sql = "SELECT * FROM daily_activity_logs WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if activity_date:
            sql += " AND activity_date = ?"
            params.append(activity_date.isoformat())
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        if team_id:
            sql += " AND team_id = ?"
            params.append(team_id)
        sql += " ORDER BY activity_date DESC, created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        logs = [self._row_to_log(row) for row in rows]
        latest: dict[tuple[str, date], DailyActivityLog] = {}
        for log in logs:
            latest.setdefault((log.agent_id, log.activity_date), log)
        return list(latest.values())

    def list_reviews(self, tenant_id: str, agent_id: str | None = None) -> list[AITrainingReview]:
        sql = "SELECT * FROM ai_training_reviews WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        reviews = [self._row_to_review(row) for row in rows]
        latest: dict[tuple[str, date], AITrainingReview] = {}
        for review in reviews:
            latest.setdefault((review.agent_id, review.review_date), review)
        return list(latest.values())

    def list_closing_scores(self, tenant_id: str, agent_id: str | None = None) -> list[ClosingScore]:
        sql = "SELECT * FROM closing_scores WHERE tenant_id = ?"
        params: list[str] = [tenant_id]
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        scores = [self._row_to_score(row) for row in rows]
        latest: dict[tuple[str, date], ClosingScore] = {}
        for score in scores:
            latest.setdefault((score.agent_id, score.score_date), score)
        return list(latest.values())

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            tenant_id=row["tenant_id"],
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=UserRole(row["role"]),
            team_id=row["team_id"],
            manager_id=row["manager_id"],
            password_hash=row["password_hash"],
        )

    def _row_to_customer(self, row: sqlite3.Row) -> Customer:
        return Customer(
            tenant_id=row["tenant_id"],
            team_id=row["team_id"],
            agent_id=row["agent_id"],
            name=row["name"],
            stage=CustomerStage(row["stage"]),
            phone=row["phone"] or "",
            notes=row["notes"] or "",
            next_meeting_date=_parse_date(row["next_meeting_date"]),
            id=row["id"],
            created_at=_parse_datetime(row["created_at"]),
        )

    def _row_to_followup(self, row: sqlite3.Row) -> CustomerFollowup:
        return CustomerFollowup(
            tenant_id=row["tenant_id"],
            customer_id=row["customer_id"],
            agent_id=row["agent_id"],
            note=row["note"],
            next_action=row["next_action"] or "",
            created_at=_parse_datetime(row["created_at"]),
            id=row["id"],
        )

    def _row_to_log(self, row: sqlite3.Row) -> DailyActivityLog:
        return DailyActivityLog(
            tenant_id=row["tenant_id"],
            team_id=row["team_id"],
            agent_id=row["agent_id"],
            activity_date=_parse_date(row["activity_date"]) or date.today(),
            call_count=row["call_count"],
            whatsapp_count=row["whatsapp_count"],
            appointment_count=row["appointment_count"],
            meeting_count=row["meeting_count"],
            closing_count=row["closing_count"],
            notes=row["notes"] or "",
            id=row["id"],
            created_at=_parse_datetime(row["created_at"]),
        )

    def _row_to_review(self, row: sqlite3.Row) -> AITrainingReview:
        return AITrainingReview(
            tenant_id=row["tenant_id"],
            team_id=row["team_id"],
            agent_id=row["agent_id"],
            review_date=_parse_date(row["review_date"]) or date.today(),
            summary=row["summary"],
            improvement_advice=row["improvement_advice"],
            manager_feedback=row["manager_feedback"],
            risk_level=row["risk_level"],
            id=row["id"],
            created_at=_parse_datetime(row["created_at"]),
        )

    def _row_to_score(self, row: sqlite3.Row) -> ClosingScore:
        return ClosingScore(
            tenant_id=row["tenant_id"],
            team_id=row["team_id"],
            agent_id=row["agent_id"],
            score_date=_parse_date(row["score_date"]) or date.today(),
            hidden_score=row["hidden_score"],
            rationale=row["rationale"],
            id=row["id"],
            created_at=_parse_datetime(row["created_at"]),
        )
