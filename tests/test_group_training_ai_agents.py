from datetime import date, timedelta

from verticals.group_training.agents.closing_agent import calculate_hidden_closing_score, hidden_score_breakdown, hidden_score_risk_level
from verticals.group_training.agents.coaching_agent import build_coaching_plan
from verticals.group_training.agents.customer_opportunity_agent import analyze_customer_opportunity
from verticals.group_training.agents.manager_insight_agent import build_manager_insight
from verticals.group_training.agents.sales_performance_agent import analyze_sales_performance
from verticals.group_training.models import Customer, CustomerStage, DailyActivityLog, UserRole
from verticals.group_training.services.dashboard_service import DashboardService
from verticals.group_training.services.repository import build_in_memory_repository
from verticals.group_training.services.sqlite_repository import DEFAULT_TEAM_ID
from apps.streamlit_group_training.services.demo_dataset_service import seed_demo_dataset


TENANT_ID = "tenant_buildway_demo"


def test_hidden_score_risk_mapping_uses_lower_score_as_higher_risk():
    assert hidden_score_risk_level(0) == "Critical"
    assert hidden_score_risk_level(39) == "Critical"
    assert hidden_score_risk_level(40) == "High"
    assert hidden_score_risk_level(59) == "High"
    assert hidden_score_risk_level(60) == "Medium"
    assert hidden_score_risk_level(79) == "Medium"
    assert hidden_score_risk_level(80) == "Low"
    assert hidden_score_risk_level(100) == "Low"


def test_customer_opportunity_agent_prioritizes_hot_proposal_today_followup():
    today = date.today()
    hot_customer = Customer(
        TENANT_ID,
        DEFAULT_TEAM_ID,
        "agt_001",
        "Hot Customer",
        CustomerStage.HOT,
        next_meeting_date=today,
        notes="High potential protection case",
    )
    proposal_customer = Customer(
        TENANT_ID,
        DEFAULT_TEAM_ID,
        "agt_001",
        "Proposal Customer",
        CustomerStage.PROPOSAL,
        next_meeting_date=today + timedelta(days=2),
        notes="方案比較及保障缺口",
    )
    cold_customer = Customer(
        TENANT_ID,
        DEFAULT_TEAM_ID,
        "agt_001",
        "Cold Customer",
        CustomerStage.COLD,
        next_meeting_date=today + timedelta(days=20),
    )

    hot = analyze_customer_opportunity(hot_customer, [], [], today)
    proposal = analyze_customer_opportunity(proposal_customer, [], [], today)
    cold = analyze_customer_opportunity(cold_customer, [], [], today)

    assert hot.priority == "High"
    assert proposal.priority == "High"
    assert cold.priority == "Low"
    assert hot.opportunity_score > cold.opportunity_score
    assert hot.score_breakdown["stage_score"] > 0
    assert hot.score_breakdown["meeting_timing_score"] == 15
    assert hot.score_reason_key == "opportunity.score_reason"
    assert hot.confidence >= 60


def test_coaching_agent_high_calls_low_appointments_generates_topic():
    logs = [
        DailyActivityLog(
            TENANT_ID,
            DEFAULT_TEAM_ID,
            "agt_001",
            date.today(),
            call_count=45,
            whatsapp_count=10,
            appointment_count=1,
            meeting_count=0,
            closing_count=0,
        )
    ]
    performance = analyze_sales_performance(logs)
    plan = build_coaching_plan(performance, hidden_score=55)

    assert performance.conversion_problem_stage == "appointment_conversion"
    assert performance.team_average_comparison
    assert "appointment_rate" in performance.performance_gap
    assert performance.trend_analysis["direction"] in {"up", "down", "stable"}
    assert plan.coaching_topic_key == "coaching.topic.appointment_conversion"
    assert plan.target_metric_key == "coaching.target_metric.appointment_conversion"
    assert plan.why_this_coaching_key == "coaching.why.appointment_conversion"
    assert plan.target_metric == "12% appointment rate"
    assert plan.target_date == plan.target_deadline
    assert plan.expected_improvement_key == "coaching.expected_improvement.appointment_conversion"


def test_manager_insight_agent_returns_team_insight_and_top_lists():
    repo = build_in_memory_repository()
    seed_demo_dataset(repo, TENANT_ID, DEFAULT_TEAM_ID, "mgr_001")
    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, "mgr_001", UserRole.MANAGER)
    customers = repo.list_customers(TENANT_ID, team_id=DEFAULT_TEAM_ID)
    opportunities = [
        analyze_customer_opportunity(
            customer,
            [followup for followup in repo.list_followups(TENANT_ID) if followup.customer_id == customer.id],
            [log for log in repo.list_logs(TENANT_ID) if log.agent_id == customer.agent_id],
        )
        for customer in customers
    ]
    performances = [
        analyze_sales_performance([log for log in dashboard["daily_logs"] if log.agent_id == agent.id])
        for agent in dashboard["agents"]
    ]

    insight = build_manager_insight(
        dashboard["agents"],
        customers,
        opportunities,
        performances,
        dashboard["closing_scores"],
    )

    assert insight.top_customers
    assert len(insight.top_customers) <= 10
    assert insight.coaching_plans
    assert insight.summary_key == "manager_insight.summary"
    assert insight.insight_reason_key.startswith("manager_insight.reason.")
    assert insight.supporting_metrics["total_agents"] == len(dashboard["agents"])
    assert insight.ai_confidence >= 50


def test_agent_role_cannot_receive_hidden_scores_from_dashboard_service():
    repo = build_in_memory_repository()
    log = DailyActivityLog(TENANT_ID, DEFAULT_TEAM_ID, "agt_001", date.today(), call_count=20, appointment_count=2, meeting_count=1)
    repo.add_daily_log(log)
    DashboardService(repo).generate_reviews_for_date(TENANT_ID, date.today())

    dashboard = DashboardService(repo).manager_dashboard(TENANT_ID, "mgr_001", UserRole.AGENT)

    assert dashboard["closing_scores"] == []


def test_hidden_score_breakdown_is_explainable_and_sums_to_score():
    log = DailyActivityLog(
        TENANT_ID,
        DEFAULT_TEAM_ID,
        "agt_001",
        date.today(),
        call_count=20,
        whatsapp_count=8,
        appointment_count=3,
        meeting_count=2,
        closing_count=1,
    )

    breakdown = hidden_score_breakdown(log)
    score = calculate_hidden_closing_score(log)

    assert set(breakdown) == {
        "activity_score",
        "appointment_score",
        "meeting_score",
        "closing_score",
        "discipline_score",
    }
    assert sum(breakdown.values()) == score.hidden_score
