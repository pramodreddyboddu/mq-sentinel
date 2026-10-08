"""MQSC reply text -> attribute rows (what the tools and matchers consume)."""

from __future__ import annotations

from mq_sentinel.connectors.mqsc_parser import message_ids, parse_mqsc_reply

_CHSTATUS = """\
5724-H72 (C) Copyright IBM Corp. 1994, 2024.
Starting MQSC for queue manager PROD_QM.


     1 : DISPLAY CHSTATUS(*) ALL
AMQ8417I: Display Channel Status details.
   CHANNEL(APP.SVRCONN)                    CHLTYPE(SVRCONN)
   CONNAME(10.0.0.42(1414))                CURRENT
   STATUS(RETRYING)                        SUBSTATE( )
AMQ8417I: Display Channel Status details.
   CHANNEL(TO.PARTNER)                     CHLTYPE(SDR)
   CONNAME(partner.example.internal(1414)) CURRENT
   RQMNAME(PARTNER_QM)                     STATUS(RUNNING)
One MQSC command read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""


def test_splits_objects_on_message_lines() -> None:
    rows = parse_mqsc_reply(_CHSTATUS)
    assert [r["CHANNEL"] for r in rows] == ["APP.SVRCONN", "TO.PARTNER"]
    assert rows[0]["STATUS"] == "RETRYING"
    assert rows[1]["RQMNAME"] == "PARTNER_QM"


def test_nested_parens_and_bare_keywords() -> None:
    rows = parse_mqsc_reply(_CHSTATUS)
    assert rows[0]["CONNAME"] == "10.0.0.42(1414)"
    assert rows[1]["CONNAME"] == "partner.example.internal(1414)"
    assert rows[0]["CURRENT"] == ""
    assert rows[0]["SUBSTATE"] == ""


def test_banner_and_trailer_prose_ignored() -> None:
    rows = parse_mqsc_reply(_CHSTATUS)
    assert all("MQSC" not in r and "One" not in r and "O" not in r for r in rows)
    assert set(rows[1]) == {"CHANNEL", "CHLTYPE", "CONNAME", "CURRENT", "RQMNAME", "STATUS"}


def test_quoted_values_keep_parens_and_escaped_quotes() -> None:
    text = (
        "AMQ8409I: Display Queue details.\n"
        "   QUEUE(APP.IN)   DESCR('Orders (EU) - don''t purge')   CURDEPTH(12)\n"
    )
    (row,) = parse_mqsc_reply(text)
    assert row["DESCR"] == "'Orders (EU) - don''t purge'"
    assert row["CURDEPTH"] == "12"


def test_not_found_message_yields_no_rows() -> None:
    text = "AMQ8420I: Channel Status not found.\n"
    assert parse_mqsc_reply(text) == []
    assert message_ids(text) == ["AMQ8420I"]


def test_qmgr_and_native_ha_shapes_match_fixtures() -> None:
    qmgr = "AMQ8408I: Display Queue Manager details.\n   QMNAME(PROD_QM)   VERSION(09040000)\n"
    assert parse_mqsc_reply(qmgr) == [{"QMNAME": "PROD_QM", "VERSION": "09040000"}]

    nha = (
        "AMQ8875I: Display Native HA status details.\n"
        "   INSTANCE(PROD_QM-1)   ROLE(REPLICA)   INSYNC(NO)   BACKLOG(1024)\n"
    )
    (row,) = parse_mqsc_reply(nha)
    assert row == {"INSTANCE": "PROD_QM-1", "ROLE": "REPLICA", "INSYNC": "NO", "BACKLOG": "1024"}


def test_zos_message_ids() -> None:
    text = (
        "CSQM293I !MQ1 CSQMDRTC 1 CHANNEL STATUS FOUND MATCHING REQUEST CRITERIA\n"
        "CSQM201I !MQ1 CSQMDRTC DISPLAY CHSTATUS DETAILS\n"
        "   CHSTATUS(TO.MQ2)   CHLTYPE(SDR)   STATUS(RETRYING)\n"
        "CSQ9022I !MQ1 CSQMDRTC ' DISPLAY CHSTATUS' NORMAL COMPLETION\n"
    )
    rows = parse_mqsc_reply(text)
    assert rows == [{"CHSTATUS": "TO.MQ2", "CHLTYPE": "SDR", "STATUS": "RETRYING"}]
    assert message_ids(text) == ["CSQM293I", "CSQM201I", "CSQ9022I"]


def test_objects_without_line_breaks() -> None:
    text = (
        "AMQ8417I: Display Channel Status details. CHANNEL(A.SVRCONN) STATUS(RUNNING) "
        "AMQ8417I: Display Channel Status details. CHANNEL(B.SDR) STATUS(RETRYING)"
    )
    rows = parse_mqsc_reply(text)
    assert rows == [
        {"CHANNEL": "A.SVRCONN", "STATUS": "RUNNING"},
        {"CHANNEL": "B.SDR", "STATUS": "RETRYING"},
    ]


def test_vrmf_version_normalized() -> None:
    from mq_sentinel.topology.detect import normalize_mq_version

    assert normalize_mq_version("09040000") == "9.4.0.0"
    assert normalize_mq_version("09030005") == "9.3.0.5"
    assert normalize_mq_version("9.4.0.0") == "9.4.0.0"
    assert normalize_mq_version(None) is None
