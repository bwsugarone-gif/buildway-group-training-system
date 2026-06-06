"""
tests/test_skeleton_import.py
------------------------------
Phase 0.2 skeleton import tests.
Verifies that all new modules are importable and basic interfaces work.
Run with: python tests/test_skeleton_import.py
Or:        pytest tests/test_skeleton_import.py
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_import_config():
    """core.config must be importable and expose load_config_safe."""
    from core.config import AppConfig, load_config_safe
    config = load_config_safe()
    assert isinstance(config, AppConfig)
    # Safe loader should not raise even with missing env vars
    assert isinstance(config.supabase_url, str)
    assert isinstance(config.openai_api_key, str)
    print("  ✓ core.config imported and load_config_safe() works")


def test_import_tenant_context():
    """core.tenant.context must be importable and TenantContext must work."""
    from core.tenant.context import (
        TenantContext,
        get_current_tenant,
        validate_tenant_id,
        register_tenant,
        require_tenant,
    )

    # validate_tenant_id
    assert validate_tenant_id("not-a-uuid") is False
    assert validate_tenant_id("") is False
    assert validate_tenant_id("123e4567-e89b-12d3-a456-426614174000") is True

    # register and retrieve
    tid = "123e4567-e89b-12d3-a456-426614174000"
    ctx = register_tenant(tid, tenant_name="Test Co", industry="crm")
    assert isinstance(ctx, TenantContext)
    assert ctx.tenant_id == tid

    retrieved = get_current_tenant(tid)
    assert retrieved is not None
    assert retrieved.tenant_name == "Test Co"

    # require_tenant on active tenant
    required = require_tenant(tid)
    assert required.tenant_id == tid

    print("  ✓ core.tenant.context imported and TenantContext works")


def test_import_memory_base():
    """core.memory.base must be importable and InMemoryMemory must work."""
    from core.memory.base import BaseMemory, InMemoryMemory, Session, Message

    mem = InMemoryMemory()
    assert isinstance(mem, BaseMemory)

    # save and load session
    session = Session(tenant_id="tenant-1", customer_ref="+85291234567", channel="whatsapp")
    session_id = mem.save_session(session)
    assert session_id == session.id

    sessions = mem.load_sessions("tenant-1")
    assert len(sessions) == 1

    # save and load message
    msg = Message(session_id=session_id, role="user", content="Hello")
    msg_id = mem.save_message(msg)
    assert msg_id == msg.id

    # customer memory
    memory = mem.load_customer_memory("tenant-1", "+85291234567")
    assert memory["session_count"] == 1
    assert memory["customer_ref"] == "+85291234567"

    print("  ✓ core.memory.base imported and InMemoryMemory works")


def test_import_rag_base():
    """core.rag.base must be importable and InMemoryRAG must work."""
    from core.rag.base import BaseRAG, InMemoryRAG, SearchResult

    rag = InMemoryRAG()
    assert isinstance(rag, BaseRAG)

    tid = "tenant-1"
    kb_id = "kb-faq-001"

    # ingest
    doc_id = rag.ingest_document(tid, kb_id, "What is MOQ? Minimum order quantity is 100 units.")
    assert isinstance(doc_id, str)

    # search — should find the document
    results = rag.search_knowledge(tid, kb_id, "MOQ minimum order")
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    assert results[0].score > 0

    # cross-tenant isolation — different tenant should get no results
    results_other = rag.search_knowledge("other-tenant", kb_id, "MOQ minimum order")
    assert len(results_other) == 0

    # delete
    deleted = rag.delete_knowledge_base(tid, kb_id)
    assert deleted is True
    results_after = rag.search_knowledge(tid, kb_id, "MOQ")
    assert len(results_after) == 0

    print("  ✓ core.rag.base imported and InMemoryRAG works")


if __name__ == "__main__":
    print("\nRunning Phase 0.2 skeleton import tests...\n")
    tests = [
        test_import_config,
        test_import_tenant_context,
        test_import_memory_base,
        test_import_rag_base,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            print(f"  ✗ {test.__name__} FAILED: {exc}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    else:
        print("All tests passed ✓")
